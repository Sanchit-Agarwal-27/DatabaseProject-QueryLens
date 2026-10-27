"""
EXPLAIN plan capture.

capture_plan(query) runs:
1. EXPLAIN FORMAT=JSON  -> access type, key used, rows examined
2. EXPLAIN ANALYZE      -> actual runtime (MySQL 8.0.18+; SELECT only, because
                           it really executes the query)
"""

import json
import re
import time as time_module
from db.connection import get_connection


def _extract_table_nodes(block, nodes):
    if isinstance(block, dict):
        if "table" in block and isinstance(block["table"], dict):
            nodes.append(block["table"])
        for value in block.values():
            _extract_table_nodes(value, nodes)
    elif isinstance(block, list):
        for item in block:
            _extract_table_nodes(item, nodes)


def _parse_explain_json(explain_json: dict) -> list:
    nodes = []
    _extract_table_nodes(explain_json.get("query_block", {}), nodes)
    return [{
        "table": n.get("table_name"),
        "access_type": n.get("access_type", "unknown"),
        "key_used": n.get("key"),
        "rows_examined": n.get("rows_examined_per_scan"),
        "filtered_pct": n.get("filtered"),
        "using_temp_or_filesort": bool(n.get("using_temporary_table") or n.get("using_filesort")),
    } for n in nodes]


def _parse_explain_analyze_text(text: str) -> dict:
    # The outermost operation is the first line that has "actual time="
    line = next((l for l in text.splitlines() if "actual time=" in l), text.splitlines()[0])
    t = re.search(r"actual time=[\d.]+\.\.([\d.]+)", line)
    r = re.search(r"rows=(\d+)\s+loops", line)
    l = re.search(r"loops=(\d+)", line)
    return {
        "actual_time_ms": float(t.group(1)) if t else None,
        "actual_rows": int(r.group(1)) if r else None,
        "loops": int(l.group(1)) if l else None,
        "raw_tree": text,
    }


def capture_plan(query: str, run_analyze: bool = True) -> dict:
    query = query.strip().rstrip(";")
    conn = get_connection()
    result = {"query": query, "table_access": [], "actual": None, "wall_clock_ms": None}
    try:
        with conn.cursor() as cursor:
            cursor.execute(f"EXPLAIN FORMAT=JSON {query}")
            row = cursor.fetchone()
            result["table_access"] = _parse_explain_json(json.loads(row["EXPLAIN"]))

            if run_analyze and query.lower().startswith("select"):
                try:
                    start = time_module.perf_counter()
                    cursor.execute(f"EXPLAIN ANALYZE {query}")
                    analyze_row = cursor.fetchone()
                    elapsed = (time_module.perf_counter() - start) * 1000
                    result["actual"] = _parse_explain_analyze_text(list(analyze_row.values())[0])
                    result["wall_clock_ms"] = round(elapsed, 3)
                except Exception:
                    result["actual"] = None  # older MySQL: no EXPLAIN ANALYZE
    finally:
        conn.close()
    return result


def summarize_plan(plan: dict) -> str:
    lines = []
    for t in plan["table_access"]:
        flag = " [!temp/filesort]" if t["using_temp_or_filesort"] else ""
        lines.append(f"  {t['table']}: access={t['access_type']}, "
                     f"key={t['key_used'] or 'NONE (full scan)'}, "
                     f"rows_examined={t['rows_examined']}{flag}")
    if plan["actual"]:
        lines.append(f"  actual: {plan['actual']['actual_rows']} rows in "
                     f"{plan['actual']['actual_time_ms']} ms (wall clock: {plan['wall_clock_ms']} ms)")
    return "\n".join(lines)


if __name__ == "__main__":
    q = "SELECT * FROM employees WHERE department_id = 3"
    print(f"Query: {q}\n")
    print(summarize_plan(capture_plan(q)))
