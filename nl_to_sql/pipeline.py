"""
NL-to-SQL using a LOCAL Ollama model (no API key, no internet needed
once the model is downloaded).

generate_sql(nl_query) -> str is the only thing the rest of the project
needs. Replace its body with your own logic any time.
"""

import os
import re
import requests
from dotenv import load_dotenv

load_dotenv()

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")

SYSTEM_PROMPT = """You convert questions into MySQL 8 queries for this HR database.
Use MySQL syntax only (no ILIKE, RETURNING, SERIAL, :: casts).

Tables:
locations(location_id, city, state, country)
departments(department_id, department_name, location_id -> locations)
job_titles(job_title_id, title_name, min_salary, max_salary)
employees(employee_id, first_name, last_name, email, hire_date,
          department_id -> departments, job_title_id -> job_titles,
          manager_id -> employees)
projects(project_id, project_name, department_id -> departments, start_date, end_date)
employee_projects(employee_id -> employees, project_id -> projects, role_on_project, hours_allocated)
attendance(attendance_id, employee_id -> employees, work_date, check_in, check_out,
           status ENUM('present','absent','half_day','leave'))
payroll(payroll_id, employee_id -> employees, pay_period, base_salary, bonus, deductions, net_pay)

Department names: Engineering, Sales, Marketing, Human Resources, Finance,
Operations, Customer Support, Legal.

Examples:
Q: How many employees are in each department?
SQL: SELECT d.department_name, COUNT(*) AS employee_count FROM employees e JOIN departments d ON e.department_id = d.department_id GROUP BY d.department_name;

Q: Show employees hired after 2022 in Engineering
SQL: SELECT e.first_name, e.last_name, e.hire_date FROM employees e JOIN departments d ON e.department_id = d.department_id WHERE d.department_name = 'Engineering' AND e.hire_date > '2022-12-31';

Q: Average net pay per job title
SQL: SELECT j.title_name, AVG(p.net_pay) AS avg_net_pay FROM payroll p JOIN employees e ON p.employee_id = e.employee_id JOIN job_titles j ON e.job_title_id = j.job_title_id GROUP BY j.title_name;

Reply with ONLY one SQL statement ending in a semicolon. No explanation, no markdown."""


class OllamaError(Exception):
    pass


def _clean_sql(raw: str) -> str:
    """Small local models often add fences or chatter -- keep just the SQL."""
    text = raw.replace("```sql", "").replace("```", "").strip()
    match = re.search(r"\b(SELECT|INSERT|UPDATE|DELETE|WITH)\b", text, re.IGNORECASE)
    if match:
        text = text[match.start():]
    if ";" in text:
        text = text[: text.index(";") + 1]
    return text.strip()


def generate_sql(nl_query: str) -> str:
    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": OLLAMA_MODEL,
                "stream": False,
                "options": {"temperature": 0},
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": nl_query},
                ],
            },
            timeout=180,
        )
    except requests.exceptions.ConnectionError:
        raise OllamaError(
            "Can't reach Ollama. Make sure it is running (open the Ollama app, "
            f"or run `ollama serve`) and OLLAMA_URL is correct: {OLLAMA_URL}"
        )

    if resp.status_code == 404:
        raise OllamaError(
            f"Model '{OLLAMA_MODEL}' isn't downloaded yet. Run: ollama pull {OLLAMA_MODEL}"
        )
    resp.raise_for_status()
    return _clean_sql(resp.json()["message"]["content"])


def get_query_type(sql: str) -> str:
    words = sql.strip().split()
    first = words[0].upper() if words else ""
    return first if first in ("SELECT", "INSERT", "UPDATE", "DELETE") else "UNKNOWN"


if __name__ == "__main__":
    q = "Show me all employees in the Engineering department hired after 2022"
    sql = generate_sql(q)
    print(f"NL:   {q}\nSQL:  {sql}\nType: {get_query_type(sql)}")
