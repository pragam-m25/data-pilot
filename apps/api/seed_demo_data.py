import os
import duckdb
from app.core.database import SessionLocal, Base, engine
from app.models.models import User, Workspace, WorkspaceMember, DataSource, DataSourceColumn, MetricDefinition, BusinessTerm, QueryHistory, DashboardReport, ReportWidget
from app.services.ingestion.file_parser import parse_file
from app.services.ingestion.profiler import run_full_profile

db = SessionLocal()
Base.metadata.create_all(bind=engine)

# 1. Ensure User & Workspace
user = db.query(User).filter(User.email == "demo@datapilot.dev").first()
if not user:
    from app.core.security import get_password_hash
    user = User(
        email="demo@datapilot.dev",
        name="Alex Demo",
        password_hash=get_password_hash("datapilot123"),
        role="admin"
    )
    db.add(user)
    db.commit()
    db.refresh(user)

ws = db.query(Workspace).filter(Workspace.owner_id == user.id).first()
if not ws:
    ws = Workspace(name="Primary Workspace", slug="primary-ws", owner_id=user.id)
    db.add(ws)
    db.commit()
    db.refresh(ws)

# 2. Create sample CSV
sample_csv = "./data/uploads/saas_orders_sample.csv"
os.makedirs("./data/uploads", exist_ok=True)
if not os.path.exists(sample_csv):
    with open(sample_csv, "w") as f:
        f.write("""order_id,region,plan,amount,customer_id,status,created_at
1001,US,Enterprise,2400.00,CUST_01,paid,2024-01-15
1002,US,Team,350.00,CUST_02,paid,2024-01-16
1003,EU,Enterprise,3100.00,CUST_03,paid,2024-01-18
1004,APAC,Pro,85.00,CUST_04,paid,2024-01-20
1005,US,Team,350.00,CUST_05,paid,2024-01-22
1006,EU,Pro,95.00,CUST_06,cancelled,2024-01-25
1007,APAC,Enterprise,2800.00,CUST_07,paid,2024-02-02
1008,US,Enterprise,2400.00,CUST_08,paid,2024-02-05
1009,LATAM,Team,320.00,CUST_09,paid,2024-02-10
1010,EU,Team,350.00,CUST_10,paid,2024-02-12
1011,APAC,Enterprise,4200.00,CUST_11,paid,2024-02-15
1012,US,Pro,85.00,CUST_12,paid,2024-02-18
""")

# 3. Register DataSource if not already present
src = db.query(DataSource).filter(DataSource.workspace_id == ws.id).first()
if not src:
    source_id = "saas_orders_v1"
    parsed = parse_file(sample_csv, "csv", source_id=source_id)
    profile = run_full_profile(f"./data/duckdb/{source_id}.duckdb", "source_data")
    src = DataSource(
        id=source_id,
        workspace_id=ws.id,
        name="SaaS Operational Orders (Verified)",
        file_path=sample_csv,
        file_type="csv",
        duckdb_table="source_data",
        row_count=parsed.row_count,
        column_count=parsed.column_count,
        profile_json=profile,
        quality_checks_json=profile.get("quality_checks", []),
        status="ready"
    )
    db.add(src)
    db.commit()
    db.refresh(src)

    for pos, col in enumerate(parsed.columns):
        c_dict = col if isinstance(col, dict) else col.__dict__
        col_rec = DataSourceColumn(
            source_id=src.id,
            name=c_dict["name"],
            inferred_type=c_dict["inferred_type"],
            position=pos,
            null_count=c_dict.get("null_count", 0),
            null_pct=0.0,
            distinct_count=c_dict.get("distinct_count", 0),
            min_val=str(c_dict.get("min")),
            max_val=str(c_dict.get("max")),
            mean_val=c_dict.get("mean"),
            std_val=c_dict.get("std"),
            top_values_json=c_dict.get("sample_values", [])
        )
        db.add(col_rec)
    db.commit()

# 4. Create approved MetricDefinition
metric = db.query(MetricDefinition).filter(MetricDefinition.workspace_id == ws.id).first()
if not metric:
    metric = MetricDefinition(
        id="metric_net_rev",
        workspace_id=ws.id,
        name="Net Revenue",
        description="Total recognized revenue excluding cancelled and refunded orders.",
        formula_sql="SUM(amount)",
        source_tables_json=["source_data"],
        grain="order",
        time_column="created_at",
        default_filters_json=[{"column": "status", "op": "!=", "val": "cancelled"}],
        allowed_dimensions_json=["region", "plan"],
        unit="USD",
        currency="$",
        owner="Finance Team",
        status="approved",
        version=1,
        approved_by="Finance Lead"
    )
    db.add(metric)
    db.commit()
    db.refresh(metric)

# 5. Create approved Glossary Term
term = db.query(BusinessTerm).filter(BusinessTerm.workspace_id == ws.id).first()
if not term:
    term = BusinessTerm(
        id="term_paid_order",
        workspace_id=ws.id,
        name="Paid Order",
        definition="An order that completed processing and is not cancelled or refunded.",
        synonyms_json=["completed order", "captured revenue"],
        related_table="source_data",
        related_column="status",
        owner="Finance",
        status="approved",
        approved_by="Finance Lead"
    )
    db.add(term)
    db.commit()

# 6. Execute a verified query into QueryHistory
query_hist = db.query(QueryHistory).filter(QueryHistory.workspace_id == ws.id).first()
if not query_hist:
    from app.services.query.nl_resolver import execute_duckdb_query
    sql = 'SELECT "region", SUM(amount) AS metric_value FROM source_data WHERE "status" != \'cancelled\' GROUP BY "region" ORDER BY metric_value DESC LIMIT 50'
    res = execute_duckdb_query(f"./data/duckdb/{src.id}.duckdb", sql)
    query_hist = QueryHistory(
        workspace_id=ws.id,
        user_id=user.id,
        question="What is our net revenue by region?",
        metric_def_id=metric.id,
        source_id=src.id,
        generated_sql=sql,
        validation_status="valid",
        status="executed",
        result_rows_json=res["rows"],
        result_columns_json=res["columns"],
        execution_ms=res["execution_ms"],
        row_count=res["row_count"],
        how_calculated_json={
            "metric_name": metric.name,
            "version": metric.version,
            "source_dataset": src.name,
            "source_type": src.file_type,
            "default_filters": metric.default_filters_json,
            "execution_ms": res["execution_ms"],
            "timestamp": "2024-02-20T10:00:00Z"
        }
    )
    db.add(query_hist)
    db.commit()
    db.refresh(query_hist)

# 7. Create sample Report
report = db.query(DashboardReport).filter(DashboardReport.workspace_id == ws.id).first()
if not report:
    report = DashboardReport(
        workspace_id=ws.id,
        title="Verified Operational Performance",
        description="Core financial and regional breakdown backed by approved metrics.",
        created_by="Alex Demo"
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    widget = ReportWidget(
        report_id=report.id,
        title="Net Revenue by Region",
        widget_type="bar",
        query_id=query_hist.id,
        metric_def_id=metric.id,
        position=0
    )
    db.add(widget)
    db.commit()

print("Seeding complete. Verifiable data ready!")
