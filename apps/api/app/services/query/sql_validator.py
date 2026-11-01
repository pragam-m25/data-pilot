"""
Deterministic SQL AST Validator using sqlglot.
Strictly enforces read-only operations, blocks DDL/DML, and enforces bounded execution.
"""
from __future__ import annotations

from typing import List, Optional, Set
import sqlglot
from sqlglot import exp

class SQLValidationError(Exception):
    pass

def validate_and_format_sql(
    query_sql: str,
    dialect: str = "duckdb",
    allowed_tables: Optional[Set[str]] = None,
    row_limit: int = 100
) -> str:
    """
    Validate SQL AST and inject safety bounds.
    Returns cleaned, validated SQL.
    Raises SQLValidationError if unsafe.
    """
    cleaned = query_sql.strip()
    if not cleaned:
        raise SQLValidationError("Query cannot be empty.")

    try:
        parsed_statements = sqlglot.parse(cleaned, read=dialect)
    except Exception as e:
        raise SQLValidationError(f"SQL Syntax Error: {str(e)}")

    if not parsed_statements or parsed_statements[0] is None:
        raise SQLValidationError("Empty or unparseable SQL statement.")

    if len(parsed_statements) > 1:
        raise SQLValidationError("Multiple SQL statements are blocked for security.")

    stmt = parsed_statements[0]

    # Block non-SELECT statements
    if not isinstance(stmt, exp.Select):
        stmt_type = type(stmt).__name__
        raise SQLValidationError(
            f"Blocked operation: Only SELECT statements are permitted. Detected statement type '{stmt_type}'."
        )

    # Check for dangerous expressions or functions
    dangerous_keywords = {"INTO", "SLEEP", "BENCHMARK", "PG_SLEEP", "COPY", "LOAD", "WRITE_CSV"}
    for node in stmt.walk():
        if isinstance(node, (exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Create, exp.Alter)):
            raise SQLValidationError("Write or DDL command detected inside query AST.")
        if isinstance(node, exp.Anonymous):
            func_name = node.name.upper()
            if func_name in dangerous_keywords:
                raise SQLValidationError(f"Unsafe function '{func_name}' is blocked.")

    # Check table whitelist if provided
    if allowed_tables:
        found_tables = {
            t.name.lower()
            for t in stmt.find_all(exp.Table)
            if t.name
        }
        # Normalize allowed tables
        norm_allowed = {t.lower() for t in allowed_tables}
        # Also allow standard CTEs defined in the same query
        cte_names = {
            cte.alias.lower()
            for cte in stmt.find_all(exp.CTE)
            if cte.alias
        }
        disallowed = found_tables - norm_allowed - cte_names
        if disallowed:
            raise SQLValidationError(
                f"Query references unapproved table(s): {', '.join(disallowed)}. Allowed: {', '.join(allowed_tables)}"
            )

    # Enforce row limit
    if not stmt.args.get("limit"):
        stmt = stmt.limit(row_limit)
    else:
        # Cap existing limit if higher than 1000
        try:
            curr_limit = int(stmt.args["limit"].expression.this)
            if curr_limit > 1000:
                stmt = stmt.limit(1000)
        except Exception:
            stmt = stmt.limit(row_limit)

    return stmt.sql(dialect=dialect)
