import pytest
from app.services.query.sql_validator import validate_and_format_sql, SQLValidationError

def test_valid_select_allowed():
    sql = "SELECT region, SUM(amount) AS revenue FROM source_data GROUP BY region"
    validated = validate_and_format_sql(sql, dialect="duckdb", row_limit=50)
    assert "SELECT" in validated
    assert "LIMIT 50" in validated

def test_insert_blocked():
    sql = "INSERT INTO source_data (order_id, amount) VALUES (999, 100)"
    with pytest.raises(SQLValidationError) as exc:
        validate_and_format_sql(sql)
    assert "Blocked operation" in str(exc.value)

def test_drop_table_blocked():
    sql = "DROP TABLE users"
    with pytest.raises(SQLValidationError) as exc:
        validate_and_format_sql(sql)
    assert "Blocked operation" in str(exc.value)

def test_multiple_statements_blocked():
    sql = "SELECT * FROM orders; DROP TABLE customers;"
    with pytest.raises(SQLValidationError) as exc:
        validate_and_format_sql(sql)
    assert "Multiple SQL statements are blocked" in str(exc.value)

def test_unsafe_functions_blocked():
    sql = "SELECT pg_sleep(10)"
    with pytest.raises(SQLValidationError) as exc:
        validate_and_format_sql(sql)
    assert "Unsafe function" in str(exc.value)
