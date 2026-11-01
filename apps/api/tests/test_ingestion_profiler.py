import os
import tempfile
import pytest
from app.core.config import get_duckdb_path
from app.services.ingestion.file_parser import parse_file
from app.services.ingestion.profiler import run_full_profile

def test_real_csv_parsing_and_profiling():
    # Create deterministic test CSV
    csv_content = """order_id,region,amount,customer_id,status
101,US,150.00,CUST_1,paid
102,US,250.00,CUST_2,paid
103,EU,80.00,CUST_3,paid
104,APAC,320.00,CUST_4,paid
105,EU,,CUST_5,cancelled
106,US,5000.00,CUST_6,paid
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(csv_content)
        temp_path = f.name

    source_id = "test_src_001"
    duck_f = get_duckdb_path(source_id)

    try:
        res = parse_file(temp_path, "csv", source_id=source_id)

        # 1. Assertions on parse result
        assert res.row_count == 6
        assert res.column_count == 5
        assert len(res.preview_rows) == 6
        assert str(res.preview_rows[0]["order_id"]) == "101"

        # Check amount column stats (1 null out of 6)
        amount_col = next(c for c in res.columns if c.name == "amount")
        assert amount_col.null_count == 1
        assert amount_col.distinct_count == 5

        # Check order_id (0 nulls, 6 distinct -> candidate key)
        order_col = next(c for c in res.columns if c.name == "order_id")
        assert order_col.null_count == 0
        assert order_col.distinct_count == 6

        # 2. Assertions on full deterministic profiler
        profile = run_full_profile(duck_f, "source_data")

        assert profile["total_rows"] == 6
        assert profile["total_columns"] == 5
        assert "order_id" in profile["candidate_keys"]
        assert "customer_id" in profile["candidate_keys"]
        assert profile["duplicate_rows"] == 0

        # Verify outlier detection (amount=5000 is an extreme value relative to 80-320)
        amount_prof = next(c for c in profile["columns"] if c["name"] == "amount")
        assert amount_prof["outlier_candidates_count"] >= 1
        assert any(q["dimension"] == "validity" and "amount" in q["column"] for q in profile["quality_checks"])

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        if os.path.exists(duck_f):
            os.remove(duck_f)


def test_xlsx_materialization_and_xls_rejection():
    import openpyxl
    import duckdb

    # 1. Test .xls rejection
    with tempfile.NamedTemporaryFile(suffix=".xls", delete=False) as f:
        f.write(b"legacy dummy excel content")
        xls_path = f.name

    try:
        with pytest.raises(ValueError, match="Unsupported format: .xls"):
            parse_file(xls_path, "xls", source_id="test_xls_reject")
    finally:
        if os.path.exists(xls_path):
            os.remove(xls_path)

    # 2. Test real XLSX materialization
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sales"
    ws.append(["transaction_id", "country", "revenue", "is_refunded"])
    ws.append(["T001", "DE", 120.50, False])
    ws.append(["T002", "FR", 340.00, False])
    ws.append(["T003", "DE", 85.00, True])

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        xlsx_path = f.name
    wb.save(xlsx_path)
    wb.close()

    source_id = "test_src_xlsx_materialized"
    duck_f = get_duckdb_path(source_id)

    try:
        res = parse_file(xlsx_path, "xlsx", source_id=source_id)
        assert res.row_count == 3
        assert res.column_count == 4
        assert len(res.preview_rows) == 3

        # Connect directly to the DuckDB file to verify PHYSICAL table persistence
        conn = duckdb.connect(duck_f, read_only=True)
        try:
            # Must be a real table, not a view dependent on deleted temp file
            tables = conn.execute("SHOW TABLES").fetchall()
            table_names = [t[0] for t in tables]
            assert "source_data" in table_names

            # Execute real query on DuckDB table
            rows = conn.execute("SELECT country, SUM(revenue) FROM source_data WHERE is_refunded = False GROUP BY 1 ORDER BY 2 DESC").fetchall()
            assert len(rows) == 2
            assert rows[0][0] == "FR"
            assert float(rows[0][1]) == 340.00
            assert rows[1][0] == "DE"
            assert float(rows[1][1]) == 120.50
        finally:
            conn.close()

    finally:
        if os.path.exists(xlsx_path):
            os.remove(xlsx_path)
        if os.path.exists(duck_f):
            os.remove(duck_f)


