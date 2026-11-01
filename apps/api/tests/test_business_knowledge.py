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
