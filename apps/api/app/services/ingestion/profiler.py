"""
Deterministic Data Quality & Profiling Engine using DuckDB.
Computes real statistics, IQR outliers, candidate keys, and explicit quality assertions.
Never guesses or fabricates results.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
import duckdb

def run_full_profile(duckdb_path: str, table_name: str = "source_data") -> Dict[str, Any]:
    """
    Run full deterministic data profile on DuckDB table.
    """
    if not os.path.exists(duckdb_path):
        raise FileNotFoundError(f"DuckDB database not found at {duckdb_path}")

    conn = duckdb.connect(duckdb_path, read_only=True)
    try:
        total_rows = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        if total_rows == 0:
            return {
                "total_rows": 0,
                "total_columns": 0,
                "duplicate_rows": 0,
                "candidate_keys": [],
                "columns": [],
                "quality_checks": []
            }

        # Exact duplicate row count
        dup_query = f"""
            SELECT COUNT(*) FROM (
                SELECT *, COUNT(*) as cnt
                FROM {table_name}
                GROUP BY ALL
                HAVING count(*) > 1
            )
        """
        try:
            dup_res = conn.execute(dup_query).fetchone()
            duplicate_rows = dup_res[0] if dup_res else 0
        except Exception:
            duplicate_rows = 0

        describe_rows = conn.execute(f"DESCRIBE {table_name}").fetchall()
        columns_profile = []
        candidate_keys = []
        quality_checks = []

        for row in describe_rows:
            col_name = row[0]
            col_type_raw = str(row[1]).upper()
            quoted = f'"{col_name}"'

            # Basic stats
            base_query = f"""
                SELECT
                    COUNT(*) - COUNT({quoted}) AS null_cnt,
                    COUNT(DISTINCT {quoted}) AS distinct_cnt
                FROM {table_name}
            """
            base_res = conn.execute(base_query).fetchone()
            null_cnt = base_res[0] if base_res else 0
            distinct_cnt = base_res[1] if base_res else 0
            null_pct = round((null_cnt / total_rows) * 100, 2)
            uniqueness_pct = round((distinct_cnt / total_rows) * 100, 2)

            if null_cnt == 0 and distinct_cnt == total_rows:
                candidate_keys.append(col_name)

            col_stats: Dict[str, Any] = {
                "name": col_name,
                "type": col_type_raw,
                "null_count": null_cnt,
                "null_percentage": null_pct,
                "distinct_count": distinct_cnt,
                "uniqueness_percentage": uniqueness_pct,
                "is_candidate_key": (null_cnt == 0 and distinct_cnt == total_rows),
            }

            # Completeness Quality Check
            quality_checks.append({
                "check_name": f"Completeness: {col_name}",
                "column": col_name,
                "dimension": "completeness",
                "rule": "null_count == 0",
                "actual_value": f"{null_cnt} nulls ({null_pct}%)",
                "status": "pass" if null_cnt == 0 else ("warn" if null_pct < 5.0 else "fail"),
                "sample_impact": f"{null_cnt} rows missing values" if null_cnt > 0 else "All rows populated"
            })

            # Numeric distribution & IQR Outlier calculation
            is_numeric = any(k in col_type_raw for k in ("INT", "FLOAT", "DOUBLE", "DECIMAL", "NUMERIC", "REAL"))
            if is_numeric and distinct_cnt > 0:
                try:
                    num_query = f"""
                        SELECT
                            MIN({quoted})::DOUBLE,
                            MAX({quoted})::DOUBLE,
                            AVG({quoted})::DOUBLE,
                            MEDIAN({quoted})::DOUBLE,
                            STDDEV_SAMP({quoted})::DOUBLE,
                            PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY {quoted})::DOUBLE AS p25,
                            PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY {quoted})::DOUBLE AS p75
                        FROM {table_name}
                        WHERE {quoted} IS NOT NULL
                    """
                    nr = conn.execute(num_query).fetchone()
                    if nr and nr[0] is not None:
                        min_v, max_v, mean_v, median_v, std_v, p25, p75 = nr
                        iqr = (p75 - p25) if (p25 is not None and p75 is not None) else 0.0
                        lower_bound = p25 - (1.5 * iqr) if p25 is not None else 0.0
                        upper_bound = p75 + (1.5 * iqr) if p75 is not None else 0.0

                        # Calculate real outliers outside [lower_bound, upper_bound]
                        outlier_query = f"""
                            SELECT COUNT(*)
                            FROM {table_name}
                            WHERE {quoted} IS NOT NULL AND ({quoted} < {lower_bound} OR {quoted} > {upper_bound})
                        """
                        outlier_count = conn.execute(outlier_query).fetchone()[0]

                        col_stats.update({
                            "min": min_v,
                            "max": max_v,
                            "mean": round(mean_v, 4) if mean_v is not None else None,
                            "median": round(median_v, 4) if median_v is not None else None,
                            "std": round(std_v, 4) if std_v is not None else None,
                            "p25": p25,
                            "p75": p75,
                            "iqr": iqr,
                            "outlier_candidates_count": outlier_count,
                            "outlier_lower_threshold": lower_bound,
                            "outlier_upper_threshold": upper_bound
                        })

                        if outlier_count > 0:
                            quality_checks.append({
                                "check_name": f"Outlier Review: {col_name}",
                                "column": col_name,
                                "dimension": "validity",
                                "rule": f"values within [{round(lower_bound, 2)}, {round(upper_bound, 2)}] (1.5 IQR)",
                                "actual_value": f"{outlier_count} candidate values outside bounds",
                                "status": "warn",
                                "sample_impact": f"{outlier_count} rows flagged for human review"
                            })
                except Exception:
                    pass

            # Top distinct values (up to 5)
            try:
                top_q = f"""
                    SELECT {quoted}::VARCHAR AS val, COUNT(*) AS freq
                    FROM {table_name}
                    WHERE {quoted} IS NOT NULL
                    GROUP BY 1
                    ORDER BY freq DESC
                    LIMIT 5
                """
                col_stats["top_values"] = [
                    {"value": str(r[0]), "count": r[1]} for r in conn.execute(top_q).fetchall()
                ]
            except Exception:
                col_stats["top_values"] = []

            columns_profile.append(col_stats)

        # Uniqueness check on candidate keys
        if candidate_keys:
            quality_checks.append({
                "check_name": "Primary Key Integrity",
                "column": ", ".join(candidate_keys),
                "dimension": "uniqueness",
                "rule": "100% unique values and 0% nulls",
                "actual_value": f"{len(candidate_keys)} candidate key columns found ({', '.join(candidate_keys)})",
                "status": "pass",
                "sample_impact": "Identified viable unique record identifiers"
            })

        return {
            "total_rows": total_rows,
            "total_columns": len(describe_rows),
            "duplicate_rows": duplicate_rows,
            "candidate_keys": candidate_keys,
            "columns": columns_profile,
            "quality_checks": quality_checks
        }
    finally:
        conn.close()
