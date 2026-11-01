from typing import Any, Dict, List, Optional
import sqlglot
from sqlglot import exp
from sqlalchemy.orm import Session

from app.models.models import DataSource, DataSourceColumn

ALLOWED_OPERATORS = {"=", "!=", "<>", ">", "<", ">=", "<=", "in", "like", "ilike", "is null", "is not null"}
ALLOWED_AGGREGATES = (exp.Sum, exp.Count, exp.Avg, exp.Min, exp.Max)

class MetricValidationError(Exception):
    pass

def validate_metric_formula_and_schema(
    formula_sql: str,
    source_tables: List[str],
    default_filters: List[Dict[str, Any]],
    allowed_dimensions: List[str],
    workspace_id: str,
    db: Session
) -> Dict[str, Any]:
    """
    Deterministically validate metric formula AST, aggregations,
    filter operators, and column references against the workspace schema.
    """
    formula = formula_sql.strip()
    if not formula:
        raise MetricValidationError("Metric formula cannot be empty.")

    # 1. Parse formula AST
    try:
        parsed = sqlglot.parse_one(formula, read="duckdb")
    except Exception as e:
        raise MetricValidationError(f"Invalid SQL formula syntax: {str(e)}")

    # 2. Check for required aggregate function
    has_agg = any(isinstance(node, ALLOWED_AGGREGATES) for node in parsed.walk())
    if not has_agg:
        raise MetricValidationError(
            f"Metric formula '{formula}' must contain at least one valid aggregation function "
            "(SUM, COUNT, AVG, MIN, MAX)."
        )

    # 3. Extract columns referenced in the formula
    formula_columns = [col.name.lower() for col in parsed.find_all(exp.Column)]

    # 4. Resolve source table columns in workspace to validate schema binding
    # Look for matching DataSource in the workspace
    target_source: Optional[DataSource] = None
    if source_tables:
        table_name = source_tables[0]
        # Match by name or duckdb_table
        target_source = db.query(DataSource).filter(
            DataSource.workspace_id == workspace_id,
            (DataSource.name == table_name) | (DataSource.duckdb_table == table_name)
        ).first()

    # If no specific source name matched, check any ready source in the workspace
    if not target_source:
        target_source = db.query(DataSource).filter(
            DataSource.workspace_id == workspace_id,
            DataSource.status == "ready"
        ).first()

    known_columns = set()
    if target_source:
        cols = db.query(DataSourceColumn.name).filter(DataSourceColumn.source_id == target_source.id).all()
        known_columns = {c[0].lower() for c in cols}

    # If we have verified columns for the table, enforce schema references
    if known_columns:
        for col in formula_columns:
            if col not in known_columns:
                raise MetricValidationError(
                    f"Referenced column '{col}' does not exist in source table "
                    f"'{target_source.name}'. Available columns: {sorted(list(known_columns))}."
                )

    # 5. Validate default_filters structure, operators, and column references
    for f in default_filters:
        if not isinstance(f, dict):
            raise MetricValidationError("Default filters must be a list of filter objects.")
        
        col = f.get("column")
        op = str(f.get("op") or f.get("operator") or "").lower().strip()
        val = f.get("val") if "val" in f else f.get("value")

        if not col:
            raise MetricValidationError("Every filter must specify a 'column'.")

        if op not in ALLOWED_OPERATORS:
            raise MetricValidationError(
                f"Unsupported filter operator '{op}' for column '{col}'. "
                f"Supported operators: {sorted(list(ALLOWED_OPERATORS))}."
            )

        if known_columns and col.lower() not in known_columns:
            raise MetricValidationError(
                f"Filter column '{col}' does not exist in source table '{target_source.name}'."
            )

    # 6. Validate allowed_dimensions against known columns
    if known_columns:
        for dim in allowed_dimensions:
            if dim.lower() not in known_columns:
                raise MetricValidationError(
                    f"Dimension column '{dim}' does not exist in source table '{target_source.name}'."
                )

    return {
        "valid": True,
        "formula_columns": formula_columns,
        "bound_source": target_source.name if target_source else None
    }
