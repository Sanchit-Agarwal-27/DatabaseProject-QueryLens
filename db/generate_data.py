"""
Populates the HR schema with synthetic data (Faker).
Run AFTER the schema exists:  python -m db.generate_data
~5,000 employees, ~120,000 attendance rows, ~60,000 payroll rows.
"""

import random
from datetime import date, timedelta, time
from faker import Faker
from db.connection import get_connection

fake = Faker()
Faker.seed(42)
random.seed(42)

NUM_LOCATIONS = 6
NUM_DEPARTMENTS = 8
NUM_JOB_TITLES = 15
NUM_EMPLOYEES = 5000
NUM_PROJECTS = 200
NUM_ATTENDANCE_ROWS = 120_000
NUM_PAYROLL_ROWS = 60_000
BATCH_SIZE = 2000


def _flush(cursor, sql, rows):
    if rows:
        cursor.executemany(sql, rows)
        rows.clear()


def insert_locations(cursor):
    rows = [(fake.city(), fake.state(), "India") for _ in range(NUM_LOCATIONS)]
    cursor.executemany("INSERT INTO locations (city, state, country) VALUES (%s,%s,%s)", rows)
    return list(range(1, NUM_LOCATIONS + 1))


def insert_departments(cursor, location_ids):
    names = ["Engineering", "Sales", "Marketing", "Human Resources",
             "Finance", "Operations", "Customer Support", "Legal"][:NUM_DEPARTMENTS]
    rows = [(n, random.choice(location_ids)) for n in names]
    cursor.executemany("INSERT INTO departments (department_name, location_id) VALUES (%s,%s)", rows)
    return list(range(1, NUM_DEPARTMENTS + 1))


def insert_job_titles(cursor):
    titles = [
        ("Software Engineer", 60000, 140000), ("Senior Software Engineer", 100000, 180000),
        ("Sales Executive", 40000, 90000), ("Sales Manager", 80000, 150000),
        ("Marketing Analyst", 45000, 85000), ("HR Generalist", 40000, 80000),
        ("Financial Analyst", 55000, 100000), ("Operations Manager", 70000, 130000),
        ("Support Specialist", 35000, 65000), ("Legal Counsel", 90000, 170000),
        ("Data Scientist", 80000, 160000), ("Product Manager", 90000, 170000),
        ("QA Engineer", 50000, 100000), ("DevOps Engineer", 70000, 140000),
        ("Recruiter", 40000, 75000),
    ][:NUM_JOB_TITLES]
    cursor.executemany(
        "INSERT INTO job_titles (title_name, min_salary, max_salary) VALUES (%s,%s,%s)", titles)
    return list(range(1, NUM_JOB_TITLES + 1))


def insert_employees(cursor, department_ids, job_title_ids):
    sql = """INSERT INTO employees
             (first_name, last_name, email, hire_date, department_id, job_title_id, manager_id)
             VALUES (%s,%s,%s,%s,%s,%s,%s)"""
    rows = []
    for i in range(NUM_EMPLOYEES):
        first, last = fake.first_name(), fake.last_name()
        email = f"{first.lower()}.{last.lower()}{i}@company.com"
        hire_date = fake.date_between(start_date="-8y", end_date="-1d")
        # manager must already exist (lower id) to keep the FK valid
        manager_id = random.randint(1, i) if i > 50 and random.random() > 0.15 else None
        rows.append((first, last, email, hire_date, random.choice(department_ids),
                     random.choice(job_title_ids), manager_id))
        if len(rows) >= BATCH_SIZE:
            _flush(cursor, sql, rows)
    _flush(cursor, sql, rows)
    return list(range(1, NUM_EMPLOYEES + 1))


def insert_projects(cursor, department_ids):
    rows = []
    for _ in range(NUM_PROJECTS):
        start = fake.date_between(start_date="-3y", end_date="-30d")
        end = start + timedelta(days=random.randint(30, 400)) if random.random() > 0.3 else None
        rows.append((fake.bs().title(), random.choice(department_ids), start, end))
    cursor.executemany(
        "INSERT INTO projects (project_name, department_id, start_date, end_date) VALUES (%s,%s,%s,%s)",
        rows)
    return list(range(1, NUM_PROJECTS + 1))


def insert_employee_projects(cursor, employee_ids, project_ids):
    sql = """INSERT INTO employee_projects (employee_id, project_id, role_on_project, hours_allocated)
             VALUES (%s,%s,%s,%s)"""
    roles = ["Contributor", "Lead", "Reviewer", "Coordinator"]
    rows, seen = [], set()
    for emp_id in employee_ids:
        for _ in range(random.randint(1, 3)):
            proj_id = random.choice(project_ids)
            if (emp_id, proj_id) in seen:
                continue
            seen.add((emp_id, proj_id))
            rows.append((emp_id, proj_id, random.choice(roles), random.randint(5, 40)))
        if len(rows) >= BATCH_SIZE:
            _flush(cursor, sql, rows)
    _flush(cursor, sql, rows)


def insert_attendance(cursor, employee_ids):
    sql = """INSERT INTO attendance (employee_id, work_date, check_in, check_out, status)
             VALUES (%s,%s,%s,%s,%s)"""
    statuses = ["present"] * 85 + ["absent"] * 5 + ["half_day"] * 5 + ["leave"] * 5
    rows = []
    for _ in range(NUM_ATTENDANCE_ROWS):
        status = random.choice(statuses)
        check_out = (time(random.randint(17, 19), random.randint(0, 59))
                     if status in ("present", "half_day") else None)
        rows.append((random.choice(employee_ids),
                     date.today() - timedelta(days=random.randint(0, 730)),
                     time(random.randint(8, 10), random.randint(0, 59)),
                     check_out, status))
        if len(rows) >= BATCH_SIZE:
            _flush(cursor, sql, rows)
    _flush(cursor, sql, rows)


def insert_payroll(cursor, employee_ids):
    sql = """INSERT INTO payroll (employee_id, pay_period, base_salary, bonus, deductions, net_pay)
             VALUES (%s,%s,%s,%s,%s,%s)"""
    rows = []
    for _ in range(NUM_PAYROLL_ROWS):
        base = round(random.uniform(35000, 180000) / 12, 2)
        bonus = round(random.uniform(0, base * 0.2), 2)
        deductions = round(base * random.uniform(0.05, 0.15), 2)
        rows.append((random.choice(employee_ids),
                     date.today().replace(day=1) - timedelta(days=30 * random.randint(0, 24)),
                     base, bonus, deductions, round(base + bonus - deductions, 2)))
        if len(rows) >= BATCH_SIZE:
            _flush(cursor, sql, rows)
    _flush(cursor, sql, rows)


def main():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            print("Inserting locations, departments, job titles...")
            location_ids = insert_locations(cursor)
            department_ids = insert_departments(cursor, location_ids)
            job_title_ids = insert_job_titles(cursor)
            print(f"Inserting {NUM_EMPLOYEES} employees...")
            employee_ids = insert_employees(cursor, department_ids, job_title_ids)
            print(f"Inserting {NUM_PROJECTS} projects + assignments...")
            project_ids = insert_projects(cursor, department_ids)
            insert_employee_projects(cursor, employee_ids, project_ids)
            print(f"Inserting {NUM_ATTENDANCE_ROWS} attendance rows (slowest step)...")
            insert_attendance(cursor, employee_ids)
            print(f"Inserting {NUM_PAYROLL_ROWS} payroll rows...")
            insert_payroll(cursor, employee_ids)
        conn.commit()
        print("Done. Data generation complete.")
    except Exception as e:
        conn.rollback()
        print(f"Failed, rolled back: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
