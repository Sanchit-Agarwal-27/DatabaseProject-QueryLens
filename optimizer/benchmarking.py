# optimizer/benchmarking.py
import time
import statistics
import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    return pymysql.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        database=os.getenv("MYSQL_DATABASE", "querylens_hr"),
        cursorclass=pymysql.cursors.DictCursor
    )

BENCHMARK_QUERIES = [
    {
        "name": "Absent in last 30 days",
        "sql": """
            SELECT employee_id, work_date, status 
            FROM attendance 
            WHERE status = 'absent' 
              AND work_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY);
        """,
        "table": "attendance",
        "index_name": "idx_att_status_date",
        "create_index_sql": "CREATE INDEX idx_att_status_date ON attendance (status, work_date);",
        "drop_index_sql": "DROP INDEX idx_att_status_date ON attendance;"
    },
    {
        "name": "Hired after 2022",
        "sql": """
            SELECT employee_id, first_name, last_name, hire_date 
            FROM employees 
            WHERE hire_date > '2022-12-31';
        """,
        "table": "employees",
        "index_name": "idx_emp_hire_date",
        "create_index_sql": "CREATE INDEX idx_emp_hire_date ON employees (hire_date);",
        "drop_index_sql": "DROP INDEX idx_emp_hire_date ON employees;"
    },
    {
        "name": "Payroll in one pay period",
        "sql": """
            SELECT employee_id, net_pay 
            FROM payroll 
            WHERE pay_period = '2024-03-01';
        """,
        "table": "payroll",
        "index_name": "idx_payroll_period",
        "create_index_sql": "CREATE INDEX idx_payroll_period ON payroll (pay_period);",
        "drop_index_sql": "DROP INDEX idx_payroll_period ON payroll;"
    }
]

def profile_query(cursor, query):
    # 1. Capture plan stats from EXPLAIN
    cursor.execute(f"EXPLAIN FORMAT=JSON {query}")
    explain_json = cursor.fetchone()
    
    # 2. Warm up
    cursor.execute(query)
    cursor.fetchall()
    
    # 3. 5 recorded runs
    times = []
    for _ in range(5):
        t0 = time.perf_counter()
        cursor.execute(query)
        cursor.fetchall()
        times.append((time.perf_counter() - t0) * 1000)
    
    median_ms = round(statistics.median(times), 2)
    return median_ms, explain_json

def run_benchmarks():
    conn = get_connection()
    cursor = conn.cursor()
    print("\n" + "="*80)
    print("QUERYLENS B+ TREE INDEX BENCHMARK SUITE")
    print("="*80 + "\n")
    
    results = []
    for test in BENCHMARK_QUERIES:
        print(f"--> Profiling: {test['name']}...")
        
        # Ensure any leftover index is dropped first
        try:
            cursor.execute(test["drop_index_sql"])
            conn.commit()
        except Exception:
            pass
            
        # Baseline (No index)
        before_ms, _ = profile_query(cursor, test["sql"])
        cursor.execute(f"EXPLAIN {test['sql']}")
        plan_before = cursor.fetchone()
        
        # Create Index
        cursor.execute(test["create_index_sql"])
        conn.commit()
        
        # Indexed run
        after_ms, _ = profile_query(cursor, test["sql"])
        cursor.execute(f"EXPLAIN {test['sql']}")
        plan_after = cursor.fetchone()
        
        # Cleanup index
        cursor.execute(test["drop_index_sql"])
        conn.commit()
        
        speedup = round(before_ms / after_ms if after_ms > 0 else 1.0, 2)
        results.append({
            "name": test["name"],
            "before_ms": f"{before_ms} ms",
            "before_type": plan_before.get("type", "ALL"),
            "before_rows": plan_before.get("rows", 0),
            "after_ms": f"{after_ms} ms",
            "after_type": plan_after.get("type", "range/ref"),
            "after_rows": plan_after.get("rows", 0),
            "speedup": f"{speedup}x"
        })
        print(f"    Done! Speedup: {speedup}x\n")
        
    conn.close()
    
    # Print formatted markdown table to paste directly into slides or report
    print("\nFINAL MEASURED RESULTS TABLE (PASTE INTO SLIDE 8):")
    print("| Query | Before (Type / Rows / Time) | After (Type / Rows / Time) | Speedup |")
    print("|---|---|---|---|")
    for r in results:
        print(f"| {r['name']} | {r['before_type']} / {r['before_rows']} / {r['before_ms']} | {r['after_type']} / {r['after_rows']} / {r['after_ms']} | {r['speedup']} |")

if __name__ == "__main__":
    run_benchmarks()