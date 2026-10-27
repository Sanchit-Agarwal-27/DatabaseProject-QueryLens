# optimizer/heuristic.py
import re

class HeuristicOptimizer:
    """
    Module 4: Heuristic (Algebraic) Query Optimization
    Demonstrates transformation from Naive canonical form to Optimized form.
    """
    
    @staticmethod
    def optimize_employee_department_query(naive_sql: str) -> dict:
        """
        Worked example: Employees in specific department hired after given date
        Transforms cross-table Cartesian join with trailing WHERE into pushed-down sub-selects.
        """
        # Rule 1: Cascade conjunctive selections (split conditions)
        # Rule 2: Push selections below join
        
        # Parse conditions using regex
        dept_match = re.search(r"department_name\s*=\s*'([^']+)'", naive_sql, re.IGNORECASE)
        hire_match = re.search(r"hire_date\s*>\s*'([^']+)'", naive_sql, re.IGNORECASE)
        
        dept_val = dept_match.group(1) if dept_match else 'Engineering'
        hire_val = hire_match.group(1) if hire_match else '2022-12-31'
        
        optimized_sql = f"""
SELECT e.first_name, e.last_name, e.hire_date, d.department_name
FROM (
    SELECT employee_id, first_name, last_name, hire_date, department_id
    FROM employees
    WHERE hire_date > '{hire_val}'
) e
JOIN (
    SELECT department_id, department_name
    FROM departments
    WHERE department_name = '{dept_val}'
) d ON e.department_id = d.department_id;
""".strip()

        return {
            "naive_sql": naive_sql,
            "optimized_sql": optimized_sql,
            "rules_applied": [
                "Cascade conjunctive selection into independent predicates",
                f"Push σ(department_name='{dept_val}') below join into departments scan",
                f"Push σ(hire_date>'{hire_val}') below join into employees scan",
                "Push π(columns) early to minimize intermediate tuple width"
            ],
            "theoretical_gain": "Reduces join inputs from (5000 x 8) Cartesian scope to (filtered employees x 1 department)."
        }

if __name__ == "__main__":
    naive = "SELECT e.first_name, e.last_name, e.hire_date FROM employees e, departments d WHERE e.department_id = d.department_id AND d.department_name = 'Engineering' AND e.hire_date > '2022-12-31';"
    opt = HeuristicOptimizer.optimize_employee_department_query(naive)
    print("--- NAIVE SQL ---")
    print(opt["naive_sql"])
    print("\n--- OPTIMIZED SQL (SELECTIONS PUSHED DOWN) ---")
    print(opt["optimized_sql"])
    print("\n--- RULES APPLIED ---")
    for r in opt["rules_applied"]:
        print(" *", r)