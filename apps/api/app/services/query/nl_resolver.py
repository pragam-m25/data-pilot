"""
Natural Language Intent Resolution and Metric Matching Engine.
Ensures every answer is tied to an approved metric definition, source table, and reproducible calculation.
Never invents formulas when missing or ambiguous.
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import duckdb
import sqlglot
from sqlglot import exp
from pydantic import BaseModel, Field

from app.core.config import get_duckdb_path
from app.models.models import MetricDefinition, BusinessTerm, DataSource
from app.services.query.sql_validator import validate_and_format_sql, SQLValidationError
from app.services.llm.factory import get_llm_adapter

logger = logging.getLogger(__name__)

class LLMIntentResolution(BaseModel):
    matched_metric_name: Optional[str] = Field(None, description="Name of the approved metric that best matches the user's intent, or null if no metric matches.")
    is_ambiguous: bool = Field(False, description="True if multiple approved metrics could match with similar likelihood.")
    candidate_metric_names: List[str] = Field(default_factory=list, description="Candidate metric names if ambiguous.")
    selected_dimensions: List[str] = Field(default_factory=list, description="Requested grouping dimensions matching the metric's allowed dimensions.")
    confidence: float = Field(0.0, description="Confidence score between 0.0 and 1.0.")
    reasoning: str = Field("", description="Brief explanation of why this approved metric was matched.")

def _resolve_with_llm(
    question: str,
    metrics: List[MetricDefinition],
    terms: List[BusinessTerm]
) -> Optional[LLMIntentResolution]:
    """
    Call configured LLM adapter with strict schema to resolve user question against approved metrics.
    Guaranteed: LLM cannot output raw SQL or numeric results; it only classifies to approved metric names.
    """
    if not metrics:
        return None

    adapter = get_llm_adapter()
    
    # Format catalog of approved metrics
    metrics_catalog = []
    for m in metrics:
        metrics_catalog.append({
            "name": m.name,
            "description": m.description or "",
            "formula": m.formula_sql,
            "grain": m.grain,
            "allowed_dimensions": m.allowed_dimensions_json or [],
            "filters": m.default_filters_json or []
        })

    terms_catalog = []
    for t in terms:
        terms_catalog.append({
            "term": t.name,
            "definition": t.definition,
            "synonyms": t.synonyms_json or []
        })

    prompt = f"""
USER QUESTION: "{question}"

APPROVED BUSINESS METRICS:
{metrics_catalog}

BUSINESS GLOSSARY & SYNONYMS:
{terms_catalog}

INSTRUCTIONS:
1. Match the question to ONE approved metric name from the list above.
2. If the user question relates to multiple approved metrics with ambiguity (e.g. asking for "revenue" when both "Gross Revenue" and "Net Revenue" exist), set is_ambiguous=True and list all candidate names.
3. If no approved metric directly covers the user inquiry, set matched_metric_name=null. NEVER invent or hallucinate a new metric name or formula.
4. If a metric is matched, select requested grouping dimensions strictly from that metric's allowed_dimensions.
"""
    try:
        # Run async complete_structured in sync wrapper
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import nest_asyncio
                nest_asyncio.apply()
                res = loop.run_until_complete(adapter.complete_structured(prompt, LLMIntentResolution))
            else:
                res = asyncio.run(adapter.complete_structured(prompt, LLMIntentResolution))
            return res
        except Exception:
            return asyncio.run(adapter.complete_structured(prompt, LLMIntentResolution))
    except Exception as e:
        logger.warning(f"LLM intent resolution fallback to deterministic matching: {e}")
        return None

def get_metric_column_requirements(metric: MetricDefinition) -> Tuple[List[str], List[str]]:
    """Extract column names required by metric's formula and default filters."""
    formula_cols = []
    try:
        parsed = sqlglot.parse_one(metric.formula_sql, read="duckdb")
        formula_cols = [col.name.lower() for col in parsed.find_all(exp.Column)]
    except Exception:
        formula_cols = []

    filter_cols = []
    if isinstance(metric.default_filters_json, list):
        for f in metric.default_filters_json:
            if isinstance(f, dict) and "column" in f:
                filter_cols.append(str(f["column"]).lower())

    return formula_cols, filter_cols

def check_metric_compatibility(
    metric: MetricDefinition,
    source: DataSource
) -> Tuple[bool, List[str]]:
    """
    Validates whether all formula and filter columns required by the metric
    actually exist in the target DataSource schema.
    """
    source_cols = {c.name.lower() for c in source.columns} if getattr(source, "columns", None) else set()
    if not source_cols:
        return True, []

    formula_cols, filter_cols = get_metric_column_requirements(metric)
    required = set(formula_cols) | set(filter_cols)
    missing = [c for c in sorted(list(required)) if c not in source_cols]
    if missing:
        return False, missing
    return True, []

def resolve_nl_query_intent(
    question: str,
    terms: List[BusinessTerm],
    metrics: List[MetricDefinition],
    source: DataSource
) -> Dict[str, Any]:
    """
    Resolves a user's natural language question against approved business definitions.
    Returns:
      - 'needs_definition': If the required business metric does not exist or has schema mismatch.
      - 'needs_clarification': If multiple conflicting metrics match.
      - 'ready_to_execute': If an approved metric is resolved cleanly.
    """
    if not metrics:
        return {
            "status": "needs_definition",
            "question": question,
            "message": "No approved metrics defined in this workspace. Please define and approve a metric first in Business Knowledge.",
            "suggested_action": "define_metric"
        }

    q_norm = question.lower().strip()
    source_cols = {c.name.lower() for c in source.columns} if getattr(source, "columns", None) else set()

    # Step 1: Attempt LLM-based structured interpretation
    llm_res = _resolve_with_llm(question, metrics, terms)

    matched_metric: Optional[MetricDefinition] = None
    selected_dims: List[str] = []

    if llm_res:
        if llm_res.is_ambiguous and llm_res.candidate_metric_names:
            candidates = [
                {"id": m.id, "name": m.name, "formula": m.formula_sql, "version": m.version}
                for m in metrics if m.name.lower() in [c.lower() for c in llm_res.candidate_metric_names]
            ]
            if len(candidates) > 1:
                return {
                    "status": "needs_clarification",
                    "question": question,
                    "message": "Multiple approved metrics match your question. Which definition should be applied?",
                    "candidates": candidates
                }

        if llm_res.matched_metric_name:
            # Check candidate metrics matching this name
            matching_name_metrics = [
                m for m in metrics if m.name.lower() == llm_res.matched_metric_name.lower()
            ]
            # Prioritize schema-compatible metric
            compatible_m = [m for m in matching_name_metrics if check_metric_compatibility(m, source)[0]]
            if compatible_m:
                matched_metric = compatible_m[0]
            elif matching_name_metrics:
                matched_metric = matching_name_metrics[0]

            if matched_metric:
                allowed = [d.lower() for d in (matched_metric.allowed_dimensions_json or [])]
                selected_dims = [d for d in llm_res.selected_dimensions if d.lower() in allowed]

    # Step 2: Deterministic fallback / confirmation
    if not matched_metric:
        matched_metrics: List[MetricDefinition] = []
        for m in metrics:
            m_name = m.name.lower()
            if m_name in q_norm:
                matched_metrics.append(m)
                continue
            for t in terms:
                if t.name.lower() == m_name or m_name in t.name.lower():
                    synonyms = t.synonyms_json if isinstance(t.synonyms_json, list) else []
                    if any(s.lower() in q_norm for s in synonyms):
                        matched_metrics.append(m)
                        break

        if not matched_metrics:
            matched_terms = [t.name for t in terms if t.name.lower() in q_norm]
            return {
                "status": "needs_definition",
                "question": question,
                "message": (
                    f"No approved metric definition found for this inquiry. "
                    f"DataPilot requires an approved metric formula before calculating numbers. "
                    + (f"Related glossary terms identified: {', '.join(matched_terms)}. " if matched_terms else "")
                    + "Please define and approve the metric in Business Knowledge."
                ),
                "suggested_action": "define_metric"
            }

        # Filter candidate metrics by schema compatibility with the target source
        compatible_matched = [m for m in matched_metrics if check_metric_compatibility(m, source)[0]]
        if compatible_matched:
            if len(compatible_matched) > 1 and len(set(m.name for m in compatible_matched)) > 1:
                candidates = [{"id": m.id, "name": m.name, "formula": m.formula_sql, "version": m.version} for m in compatible_matched]
                return {
                    "status": "needs_clarification",
                    "question": question,
                    "message": "Multiple approved metrics match your question. Which definition should be applied?",
                    "candidates": candidates
                }
            matched_metric = compatible_matched[0]
        else:
            matched_metric = matched_metrics[0]

    metric = matched_metric

    # Step 2.5: Schema compatibility validation check
    is_compat, missing_cols = check_metric_compatibility(metric, source)
    if not is_compat:
        cand_cols = sorted(list(source_cols))[:10]
        return {
            "status": "needs_definition",
            "question": question,
            "message": (
                f"Approved metric '{metric.name}' expects column(s) {missing_cols}, "
                f"which are not present in dataset '{source.name}'. "
                f"Please define an approved metric mapped to the columns of '{source.name}' in Business Knowledge."
            ),
            "suggested_action": "define_metric",
            "missing_columns": missing_cols,
            "candidate_columns": cand_cols
        }

    # Step 3: Determine dimensions requested if not already selected
    target_table = "source_data" if source.file_type in ["csv", "xlsx"] else (source.duckdb_table or "orders")
    available_dimensions = metric.allowed_dimensions_json if isinstance(metric.allowed_dimensions_json, list) else []

    if not selected_dims:
        for dim in available_dimensions:
            d_low = dim.lower()
            if d_low in q_norm or f"by {d_low}" in q_norm:
                selected_dims.append(dim)
            elif d_low.endswith("_status") and ("status" in q_norm or "by status" in q_norm):
                selected_dims.append(dim)

    # Restrict selected dimensions to columns that actually exist in the target source
    if source_cols:
        selected_dims = [d for d in selected_dims if d.lower() in source_cols]

    # Step 4: Construct reproducible, verifiable SQL
    formula = metric.formula_sql.strip()

    # Add default filters from metric definition
    where_clauses: List[str] = []
    if isinstance(metric.default_filters_json, list):
        for f in metric.default_filters_json:
            if isinstance(f, dict) and "column" in f:
                col = f['column']
                op = f.get('op') or f.get('operator') or '='
                val = f.get('val') if 'val' in f else f.get('value')
                val_repr = f"'{val}'" if isinstance(val, str) else str(val)
                where_clauses.append(f"\"{col}\" {op} {val_repr}")

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    if selected_dims:
        dim_cols = ", ".join([f'"{d}"' for d in selected_dims])
        sql_draft = f"""
            SELECT {dim_cols}, {formula} AS metric_value
            FROM {target_table}
            {where_sql}
            GROUP BY {dim_cols}
            ORDER BY metric_value DESC
            LIMIT 50;
        """
    else:
        sql_draft = f"""
            SELECT {formula} AS metric_value
            FROM {target_table}
            {where_sql};
        """

    # Step 5: AST validate SQL
    try:
        validated_sql = validate_and_format_sql(sql_draft, dialect="duckdb", row_limit=100)
    except SQLValidationError as e:
        return {
            "status": "validation_error",
            "message": f"Generated SQL failed security audit: {str(e)}",
            "raw_sql": sql_draft
        }

    # Step 6: Database Binder verification (dry-run check for DuckDB files)
    if source.file_type in ["csv", "xlsx"]:
        duckdb_path = get_duckdb_path(source.id)
        if os.path.exists(duckdb_path):
            try:
                dry_conn = duckdb.connect(duckdb_path, read_only=True)
                dry_conn.execute(f"EXPLAIN {validated_sql}")
                dry_conn.close()
            except Exception as e:
                err_msg = str(e)
                logger.warning(f"DuckDB schema binder check caught mismatch: {err_msg}")
                return {
                    "status": "validation_error",
                    "message": f"Generated SQL failed dataset schema validation: {err_msg}",
                    "raw_sql": validated_sql
                }

    explanation = (
        f"Calculates '{metric.name}' (v{metric.version}) using the approved business formula `{metric.formula_sql}`. "
        + (f"Grouped by {', '.join(selected_dims)}. " if selected_dims else "Computed across all eligible records. ")
        + (f"Applied default exclusions: {', '.join(where_clauses)}." if where_clauses else "No exclusions applied.")
    )

    return {
        "status": "ready_to_execute",
        "question": question,
        "metric_id": metric.id,
        "metric_name": metric.name,
        "metric_version": metric.version,
        "formula": metric.formula_sql,
        "sql": validated_sql,
        "dimensions": selected_dims,
        "explanation": explanation,
        "how_calculated": {
            "metric_name": metric.name,
            "version": metric.version,
            "formula_sql": metric.formula_sql,
            "source_dataset": source.name,
            "source_type": source.file_type,
            "default_filters": metric.default_filters_json,
            "generated_sql": validated_sql,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    }

def execute_duckdb_query(
    duckdb_path: str,
    sql_query: str,
    table_name: str = "source_data"
) -> Dict[str, Any]:
    """Execute validated read-only SQL on DuckDB dataset."""
    start_time = time.time()
    conn = duckdb.connect(duckdb_path, read_only=True)
    try:
        cursor = conn.execute(sql_query)
        col_names = [desc[0] for desc in cursor.description]
        rows_raw = cursor.fetchall()
        rows = [
            dict(zip(col_names, [str(v) if v is not None else None for v in r]))
            for r in rows_raw
        ]
        exec_ms = round((time.time() - start_time) * 1000, 2)
        return {
            "columns": col_names,
            "rows": rows,
            "row_count": len(rows),
            "execution_ms": exec_ms
        }
    finally:
        conn.close()
