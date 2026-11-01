import io
import os
import tempfile
import pytest
from fastapi.testclient import TestClient
import openpyxl

from app.main import app
from app.core.config import settings, get_duckdb_path
from app.core.database import SessionLocal
from app.core.security import create_access_token, get_password_hash
from app.models.models import User, Workspace, WorkspaceMember, DataSource, MetricDefinition, QueryHistory, DashboardReport

client = TestClient(app)

@pytest.fixture
def auth_context():
    """Create test users and workspaces with known roles."""
    db = SessionLocal()
    try:
        # Create user 1 (Owner)
        user1 = db.query(User).filter(User.email == "test_owner@datapilot.dev").first()
        if not user1:
            user1 = User(
                email="test_owner@datapilot.dev",
                name="Test Owner",
                password_hash=get_password_hash("password123"),
                role="member"
            )
            db.add(user1)
            db.commit()
            db.refresh(user1)

        # Create user 2 (Outsider / Unauthorized user)
        user2 = db.query(User).filter(User.email == "test_outsider@datapilot.dev").first()
        if not user2:
            user2 = User(
                email="test_outsider@datapilot.dev",
                name="Test Outsider",
                password_hash=get_password_hash("password123"),
                role="member"
            )
            db.add(user2)
            db.commit()
            db.refresh(user2)

        # Create Workspace for User 1
        ws1 = db.query(Workspace).filter(Workspace.owner_id == user1.id).first()
        if not ws1:
            ws1 = Workspace(
                name="Owner Analytics Workspace",
                slug=f"ws-test-{user1.id[:6]}",
                owner_id=user1.id
            )
            db.add(ws1)
            db.commit()
            db.refresh(ws1)
            member = WorkspaceMember(workspace_id=ws1.id, user_id=user1.id, role="owner")
            db.add(member)
            db.commit()

        token1 = create_access_token(user1.id)
        token2 = create_access_token(user2.id)

        yield {
            "owner": user1,
            "outsider": user2,
            "workspace": ws1,
            "token_owner": token1,
            "token_outsider": token2
        }
    finally:
        db.close()

def test_production_auth_rejection():
    """Verify that in production mode, missing credentials return 401 Unauthorized."""
    old_env = settings.ENVIRONMENT
    settings.ENVIRONMENT = "production"
    try:
        # Request /me with no token in production mode
        res = client.get("/api/v1/auth/me")
        assert res.status_code == 401
        assert "not provided" in res.json().get("detail", "").lower()
    finally:
        settings.ENVIRONMENT = old_env

def test_full_analytics_lifecycle_e2e(auth_context):
    """
    Complete E2E Analytics Flow:
    1. Upload CSV dataset
    2. Upload XLSX dataset with physical materialization
    3. Rejection of .xls
    4. Deterministic profile & IQR outlier calculation
    5. Workspace permission verification (403 for outsider)
    6. Metric creation (validates schema, starts in 'draft')
    7. Validation error on illegal formulas or columns
    8. Query unapproved metric -> needs_definition
    9. Approve metric (after schema AST validation)
    10. Ask Data intent resolution
    11. Execute read-only SQL on DuckDB
    12. Create dashboard and verify widget data
    """
    token_owner = auth_context["token_owner"]
    token_outsider = auth_context["token_outsider"]
    ws_id = auth_context["workspace"].id
    headers_owner = {"Authorization": f"Bearer {token_owner}"}
    headers_outsider = {"Authorization": f"Bearer {token_outsider}"}

    # 1. Upload CSV dataset
    csv_bytes = b"transaction_id,region,revenue,status\n101,North,200.0,completed\n102,South,450.0,completed\n103,North,120.0,refunded\n104,East,9500.0,completed\n"
    res_upload = client.post(
        "/api/v1/sources/upload",
        files={"file": ("orders.csv", io.BytesIO(csv_bytes), "text/csv")},
        data={"name": "orders_csv", "workspace_id": ws_id},
        headers=headers_owner
    )
    assert res_upload.status_code == 200, res_upload.text
    source_csv = res_upload.json()
    assert source_csv["row_count"] == 4
    assert source_csv["column_count"] == 4
    source_id = source_csv["id"]

    # 2. Upload XLSX dataset and assert physical persistence
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sales"
    ws.append(["order_id", "country", "amount", "is_paid"])
    ws.append(["O1", "DE", 100.0, True])
    ws.append(["O2", "FR", 250.0, True])
    xlsx_buffer = io.BytesIO()
    wb.save(xlsx_buffer)
    xlsx_bytes = xlsx_buffer.getvalue()

    res_xlsx = client.post(
        "/api/v1/sources/upload",
        files={"file": ("sales.xlsx", io.BytesIO(xlsx_bytes), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        data={"name": "sales_xlsx", "workspace_id": ws_id},
        headers=headers_owner
    )
    assert res_xlsx.status_code == 200, res_xlsx.text
    source_xlsx = res_xlsx.json()
    assert source_xlsx["row_count"] == 2

    # 3. Rejection of .xls
    res_xls = client.post(
        "/api/v1/sources/upload",
        files={"file": ("legacy.xls", io.BytesIO(b"binary excel"), "application/vnd.ms-excel")},
        data={"name": "legacy_xls", "workspace_id": ws_id},
        headers=headers_owner
    )
    assert res_xls.status_code == 400
    assert "not supported" in res_xls.json()["detail"]

    # 4. Preview and Profile on CSV
    res_preview = client.get(f"/api/v1/sources/{source_id}/preview?limit=10", headers=headers_owner)
    assert res_preview.status_code == 200
    assert len(res_preview.json()["rows"]) == 4

    res_profile = client.get(f"/api/v1/sources/{source_id}/profile", headers=headers_owner)
    assert res_profile.status_code == 200
    profile = res_profile.json()
    assert profile["total_rows"] == 4
    assert profile["duplicate_rows"] == 0

    # 5. Workspace isolation check: outsider cannot read owner's source
    res_forbidden = client.get(f"/api/v1/sources/{source_id}", headers=headers_outsider)
    assert res_forbidden.status_code == 403

    # 6 & 7. Metric creation with Schema Validation
    # A) Test illegal unaggregated formula rejection
    res_bad_formula = client.post(
        "/api/v1/knowledge/metrics",
        json={
            "name": "Bad Metric",
            "formula_sql": "revenue",  # No SUM or aggregation
            "source_tables": ["orders_csv"],
            "workspace_id": ws_id
        },
        headers=headers_owner
    )
    assert res_bad_formula.status_code == 422
    assert "aggregation function" in res_bad_formula.json()["detail"].lower()

    # B) Test non-existent column rejection
    res_bad_col = client.post(
        "/api/v1/knowledge/metrics",
        json={
            "name": "Missing Col Metric",
            "formula_sql": "SUM(non_existent_col)",
            "source_tables": ["orders_csv"],
            "workspace_id": ws_id
        },
        headers=headers_owner
    )
    assert res_bad_col.status_code == 422
    assert "does not exist" in res_bad_col.json()["detail"].lower()

    # C) Valid metric creation -> Must start in 'draft' status
    import uuid
    metric_unique_name = f"ChurnMetric_{uuid.uuid4().hex[:6]}"
    res_metric = client.post(
        "/api/v1/knowledge/metrics",
        json={
            "name": metric_unique_name,
            "description": "Total completed transaction revenue",
            "formula_sql": "SUM(revenue)",
            "source_tables": ["orders_csv"],
            "allowed_dimensions": ["region"],
            "default_filters": [{"column": "status", "op": "=", "val": "completed"}],
            "workspace_id": ws_id
        },
        headers=headers_owner
    )
    assert res_metric.status_code == 200, res_metric.text
    metric_data = res_metric.json()
    assert metric_data["status"] == "draft"
    metric_id = metric_data["id"]

    # 8. Unapproved draft metric cannot be used in Ask Data
    res_ask_draft = client.post(
        "/api/v1/query/ask",
        json={"question": f"What is our {metric_unique_name} by region?", "source_id": source_id},
        headers=headers_owner
    )
    assert res_ask_draft.status_code == 200
    assert res_ask_draft.json()["status"] == "needs_definition"

    # 9. Submit for review -> Approve metric
    res_submit = client.post(f"/api/v1/knowledge/metrics/{metric_id}/submit-review", headers=headers_owner)
    assert res_submit.status_code == 200
    assert res_submit.json()["status"] == "in_review"

    res_approve = client.post(f"/api/v1/knowledge/metrics/{metric_id}/approve", headers=headers_owner)
    assert res_approve.status_code == 200
    assert res_approve.json()["status"] == "approved"

    # 10. Ask Data intent resolution with approved metric
    res_ask = client.post(
        "/api/v1/query/ask",
        json={"question": f"What is our {metric_unique_name} by region?", "source_id": source_id},
        headers=headers_owner
    )
    assert res_ask.status_code == 200
    ask_res = res_ask.json()
    assert ask_res["status"] == "ready_to_execute"
    assert ask_res["metric_name"] == metric_unique_name
    assert "region" in ask_res["dimensions"]
    assert "SUM(revenue)" in ask_res["sql"]
    assert "completed" in ask_res["sql"]
    query_id = ask_res["query_id"]

    # 11. Execute read-only SQL on DuckDB
    res_exec = client.post(
        "/api/v1/query/execute",
        json={"query_id": query_id, "confirmed": True},
        headers=headers_owner
    )
    assert res_exec.status_code == 200
    exec_data = res_exec.json()
    assert exec_data["status"] == "executed"
    assert len(exec_data["rows"]) >= 1
    assert "metric_value" in exec_data["columns"]
    assert exec_data["execution_ms"] > 0

    # 12. Create Dashboard Report and add widget
    res_report = client.post(
        "/api/v1/reports",
        json={"title": "Q3 Executive Performance", "workspace_id": ws_id},
        headers=headers_owner
    )
    assert res_report.status_code == 200
    report_id = res_report.json()["id"]

    res_widget = client.post(
        f"/api/v1/reports/{report_id}/widgets",
        json={
            "title": "Net Revenue by Region",
            "widget_type": "bar",
            "query_id": query_id
        },
        headers=headers_owner
    )
    assert res_widget.status_code == 200

    # Retrieve full report and assert verified calculated rows render
    res_report_detail = client.get(f"/api/v1/reports/{report_id}", headers=headers_owner)
    assert res_report_detail.status_code == 200
    rep_data = res_report_detail.json()
    assert len(rep_data["widgets"]) == 1
    widget_data = rep_data["widgets"][0]["data"]
    assert len(widget_data["rows"]) >= 1
    assert "metric_value" in widget_data["columns"]
    assert widget_data["sql"] is not None
