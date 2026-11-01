"""
Real file parsing using DuckDB + openpyxl.

parse_file(file_path, file_type) → ParseResult

Supports: csv, xlsx
Uses DuckDB for all statistical calculations.
NEVER returns mock data — raises on failure.
"""
from __future__ import annotations

import os
import csv
import json
import tempfile
import traceback
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

import duckdb
import openpyxl


from app.core.config import get_duckdb_path


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ColumnInfo:
    name: str
    inferred_type: str
    null_count: int
    distinct_count: int
    sample_values: List[Any]
    min: Optional[Any] = None
    max: Optional[Any] = None
    mean: Optional[float] = None
    std: Optional[float] = None


@dataclass
class ParseResult:
    row_count: int
    column_count: int
    columns: List[ColumnInfo]
    preview_rows: List[Dict[str, Any]]
    sheet_name: Optional[str] = None

    def to_dict(self) -> Dict:
        d = asdict(self)
        # Ensure sample_values are JSON-serialisable
        for col in d["columns"]:
            col["sample_values"] = [_to_json_safe(v) for v in col["sample_values"]]
            col["min"] = _to_json_safe(col["min"])
            col["max"] = _to_json_safe(col["max"])
        for row in d["preview_rows"]:
            for k, v in row.items():
                row[k] = _to_json_safe(v)
        return d


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_json_safe(v: Any) -> Any:
    """Convert DuckDB / Python types to JSON-serialisable equivalents."""
    if v is None:
        return None
    try:
        import decimal
        if isinstance(v, decimal.Decimal):
            return float(v)
    except ImportError:
        pass
    if hasattr(v, "isoformat"):
        return v.isoformat()
    if isinstance(v, (int, float, str, bool)):
        return v
    return str(v)


def _map_duckdb_type(type_str: str) -> str:
    """Normalise DuckDB column type to a human-readable category."""
    t = type_str.upper()
    if any(k in t for k in ("INT", "BIGINT", "SMALLINT", "HUGEINT", "TINYINT")):
        return "integer"
    if any(k in t for k in ("FLOAT", "DOUBLE", "REAL", "DECIMAL", "NUMERIC")):
        return "float"
    if any(k in t for k in ("DATE",)):
        return "date"
    if any(k in t for k in ("TIMESTAMP", "TIME")):
        return "datetime"
    if any(k in t for k in ("BOOL",)):
        return "boolean"
    return "text"


def _materialize_table(conn: duckdb.DuckDBPyConnection, file_path: str) -> str:
    """Materialize a CSV file into a physical DuckDB table 'source_data'."""
    # Escape single quotes in file path for DuckDB string literal
    escaped_path = file_path.replace("'", "''")
    conn.execute("DROP VIEW IF EXISTS source_data;")
    conn.execute("DROP TABLE IF EXISTS source_data;")
    conn.execute(f"""
        CREATE TABLE source_data AS
        SELECT * FROM read_csv_auto('{escaped_path}', sample_size=10000, header=True)
    """)
    return "source_data"


# ---------------------------------------------------------------------------
# Main parse function
# ---------------------------------------------------------------------------

def parse_file(
    file_path: str,
    file_type: str,
    source_id: Optional[str] = None,
) -> ParseResult:
    """
    Parse a CSV or XLSX file and compute column statistics using DuckDB.

    Args:
        file_path:  Absolute path to the raw file.
        file_type:  "csv" or "xlsx".
        source_id:  If provided, persists a DuckDB file to data/duckdb/{source_id}.duckdb.

    Returns:
        ParseResult with full column stats and preview rows.

    Raises:
        ValueError:  For unsupported file types or bad content.
        RuntimeError: For DuckDB / IO failures.
    """
    file_type = file_type.lower().strip(".")
    if file_type == "xls":
        raise ValueError("Unsupported format: .xls. The legacy binary Excel format is not supported. Please convert your file to .xlsx or .csv.")
    if file_type not in ("csv", "xlsx"):
        raise ValueError(f"Unsupported file type: {file_type!r}. Only csv and xlsx are supported.")

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    sheet_name: Optional[str] = None
    csv_path: str = file_path  # will be overridden for xlsx

    # --- XLSX → convert to CSV via openpyxl ---------------------------------
    if file_type == "xlsx":
        wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
        sheet_name = wb.sheetnames[0]
        ws = wb[sheet_name]

        tmp_csv = tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, newline="", encoding="utf-8"
        )
        try:
            writer = csv.writer(tmp_csv)
            for row in ws.iter_rows(values_only=True):
                writer.writerow([("" if v is None else v) for v in row])
            tmp_csv.close()
            csv_path = tmp_csv.name
        except Exception as exc:
            tmp_csv.close()
            if os.path.exists(tmp_csv.name):
                os.unlink(tmp_csv.name)
            raise RuntimeError(f"Failed to convert XLSX to CSV: {exc}") from exc
        finally:
            wb.close()

    # --- Open DuckDB (persistent if source_id given) ------------------------
    if source_id:
        duckdb_path = get_duckdb_path(source_id)
        conn = duckdb.connect(duckdb_path)
    else:
        conn = duckdb.connect(":memory:")

    try:
        _materialize_table(conn, csv_path)

        # Get column names + DuckDB types via DESCRIBE
        describe_rows = conn.execute("DESCRIBE source_data").fetchall()
        # describe_rows: [(col_name, col_type, null?, key?, default, extra), ...]
        col_names = [r[0] for r in describe_rows]
        col_types_raw = [r[1] for r in describe_rows]
        col_types = [_map_duckdb_type(t) for t in col_types_raw]

        # Total row count
        total_rows = conn.execute("SELECT COUNT(*) FROM source_data").fetchone()[0]

        # Preview rows (first 10)
        preview_raw = conn.execute("SELECT * FROM source_data LIMIT 10").fetchall()
        preview_rows = [
            {col_names[i]: _to_json_safe(v) for i, v in enumerate(row)}
            for row in preview_raw
        ]

        # Per-column stats
        columns: List[ColumnInfo] = []
        for idx, (col_name, col_type) in enumerate(zip(col_names, col_types)):
            quoted = f'"{col_name}"'

            # null_count
            null_count = conn.execute(
                f"SELECT COUNT(*) FROM source_data WHERE {quoted} IS NULL"
            ).fetchone()[0]

            # distinct_count (approximate via COUNT DISTINCT)
            distinct_count = conn.execute(
                f"SELECT COUNT(DISTINCT {quoted}) FROM source_data WHERE {quoted} IS NOT NULL"
            ).fetchone()[0]

            # Sample values (up to 5 distinct non-null)
            sample_rows = conn.execute(
                f"SELECT DISTINCT {quoted} FROM source_data WHERE {quoted} IS NOT NULL LIMIT 5"
            ).fetchall()
            sample_values = [_to_json_safe(r[0]) for r in sample_rows]

            # Numeric stats
            min_val = max_val = mean_val = std_val = None
            if col_type in ("integer", "float"):
                try:
                    stats = conn.execute(
                        f"SELECT MIN({quoted}), MAX({quoted}), AVG({quoted}), STDDEV({quoted}) "
                        f"FROM source_data WHERE {quoted} IS NOT NULL"
                    ).fetchone()
                    min_val, max_val, mean_val, std_val = (
                        _to_json_safe(stats[0]),
                        _to_json_safe(stats[1]),
                        float(stats[2]) if stats[2] is not None else None,
                        float(stats[3]) if stats[3] is not None else None,
                    )
                except Exception:
                    pass
            elif col_type in ("date", "datetime"):
                try:
                    stats = conn.execute(
                        f"SELECT MIN({quoted}), MAX({quoted}) FROM source_data WHERE {quoted} IS NOT NULL"
                    ).fetchone()
                    min_val = _to_json_safe(stats[0])
                    max_val = _to_json_safe(stats[1])
                except Exception:
                    pass
            else:
                # text: min/max lexicographically
                try:
                    stats = conn.execute(
                        f"SELECT MIN({quoted}), MAX({quoted}) FROM source_data WHERE {quoted} IS NOT NULL"
                    ).fetchone()
                    min_val = _to_json_safe(stats[0])
                    max_val = _to_json_safe(stats[1])
                except Exception:
                    pass

            columns.append(ColumnInfo(
                name=col_name,
                inferred_type=col_type,
                null_count=null_count,
                distinct_count=distinct_count,
                sample_values=sample_values,
                min=min_val,
                max=max_val,
                mean=mean_val,
                std=std_val,
            ))

        result = ParseResult(
            row_count=total_rows,
            column_count=len(col_names),
            columns=columns,
            preview_rows=preview_rows,
            sheet_name=sheet_name,
        )
        return result

    except Exception as exc:
        raise RuntimeError(f"Failed to parse file '{file_path}': {exc}\n{traceback.format_exc()}") from exc
    finally:
        conn.close()
        # Clean up temp CSV if we created one from xlsx
        if file_type == "xlsx" and csv_path != file_path:
            try:
                os.unlink(csv_path)
            except OSError:
                pass
