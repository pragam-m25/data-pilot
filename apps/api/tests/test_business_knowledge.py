import pytest
from app.models.models import MetricDefinition, BusinessTerm, DataSource
from app.services.query.nl_resolver import resolve_nl_query_intent

def test_metric_resolution_when_metric_approved():
    metric = MetricDefinition(
        id="metric_rev_01",
        name="Net Revenue",
        formula_sql="SUM(amount)",
        allowed_dimensions_json=["region", "plan"],
        default_filters_json=[{"column": "status", "op": "!=", "val": "cancelled"}],
        version=1,
        status="approved"
    )
    terms = [
        BusinessTerm(
            id="term_01",
            name="Net Revenue",
            definition="Gross amount minus refunds",
            synonyms_json=["total sales", "revenue"]
        )
    ]
    source = DataSource(
        id="src_01",
        name="Orders Data",
        file_type="csv",
        duckdb_table="source_data"
    )

    # 1. Resolves cleanly for matching question
    res = resolve_nl_query_intent("What is our net revenue by region?", terms, [metric], source)
    assert res["status"] == "ready_to_execute"
    assert res["metric_name"] == "Net Revenue"
    assert "region" in res["dimensions"]
    assert "SUM(amount)" in res["sql"]
    assert "cancelled" in res["sql"]

def test_missing_metric_returns_needs_definition():
    metric = MetricDefinition(
        id="metric_rev_01",
        name="Net Revenue",
        formula_sql="SUM(amount)",
        status="approved"
    )
    terms = []
    source = DataSource(id="src_01", name="Orders Data", file_type="csv")

    # Ask for unapproved / undefined metric
    res = resolve_nl_query_intent("What is the customer lifetime value (LTV)?", terms, [metric], source)
    assert res["status"] == "needs_definition"
    assert "No approved metric definition found" in res["message"]

def test_metric_schema_mismatch_returns_needs_definition():
    from app.models.models import DataSourceColumn
    metric = MetricDefinition(
        id="metric_rev_legacy",
        name="Net Revenue",
        formula_sql="SUM(amount)",
        allowed_dimensions_json=["region"],
        default_filters_json=[{"column": "status", "op": "!=", "val": "cancelled"}],
        status="approved",
        version=1
    )
    terms = []
    source = DataSource(
        id="src_ecom_01",
        name="Ecommerce Data",
        file_type="csv",
        duckdb_table="source_data"
    )
    # Source has different columns
    source.columns = [
        DataSourceColumn(source_id="src_ecom_01", name="order_id", inferred_type="text"),
        DataSourceColumn(source_id="src_ecom_01", name="region", inferred_type="text"),
        DataSourceColumn(source_id="src_ecom_01", name="recognized_revenue_inr", inferred_type="float"),
        DataSourceColumn(source_id="src_ecom_01", name="order_status", inferred_type="text")
    ]

    res = resolve_nl_query_intent("What is our net revenue by region?", terms, [metric], source)
    assert res["status"] == "needs_definition"
    assert "expects column(s)" in res["message"]
    assert "amount" in res["missing_columns"] or "status" in res["missing_columns"]

def test_multi_source_metric_resolution_selects_compatible_metric():
    from app.models.models import DataSourceColumn
    metric_saas = MetricDefinition(
        id="metric_saas_rev",
        name="Net Revenue",
        formula_sql="SUM(amount)",
        allowed_dimensions_json=["region"],
        default_filters_json=[{"column": "status", "op": "!=", "val": "cancelled"}],
        status="approved",
        version=1
    )
    metric_ecom = MetricDefinition(
        id="metric_ecom_rev",
        name="Net Revenue",
        formula_sql="SUM(recognized_revenue_inr)",
        allowed_dimensions_json=["region"],
        default_filters_json=[{"column": "order_status", "op": "!=", "val": "Cancelled"}],
        status="approved",
        version=1
    )
    terms = []
    source = DataSource(
        id="src_ecom_01",
        name="Ecommerce Data",
        file_type="csv",
        duckdb_table="source_data"
    )
    source.columns = [
        DataSourceColumn(source_id="src_ecom_01", name="order_id", inferred_type="text"),
        DataSourceColumn(source_id="src_ecom_01", name="region", inferred_type="text"),
        DataSourceColumn(source_id="src_ecom_01", name="recognized_revenue_inr", inferred_type="float"),
        DataSourceColumn(source_id="src_ecom_01", name="order_status", inferred_type="text")
    ]

    # Should select metric_ecom because metric_saas has missing columns
    res = resolve_nl_query_intent("What is our net revenue by region?", terms, [metric_saas, metric_ecom], source)
    assert res["status"] == "ready_to_execute"
    assert res["metric_id"] == "metric_ecom_rev"
    assert "recognized_revenue_inr" in res["sql"]
    assert "order_status" in res["sql"]
    assert '"status"' not in res["sql"]
    assert "amount" not in res["sql"]

