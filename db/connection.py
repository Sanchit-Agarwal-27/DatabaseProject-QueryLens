"""One place that knows about MySQL credentials (read from .env)."""

import os
import pymysql
from dotenv import load_dotenv

load_dotenv()


def get_connection(use_database: bool = True):
    return pymysql.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        port=int(os.getenv("MYSQL_PORT", 3306)),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        database=os.getenv("MYSQL_DATABASE", "querylens_hr") if use_database else None,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )


def run_schema_file(path: str = "db/schema.sql"):
    """One-time setup: creates the querylens_hr database and all tables."""
    conn = get_connection(use_database=False)
    try:
        with open(path, "r", encoding="utf-8") as f:
            sql_script = f.read()
        with conn.cursor() as cursor:
            for statement in sql_script.split(";"):
                statement = statement.strip()
                if statement:
                    cursor.execute(statement)
        conn.commit()
        print("Schema created successfully.")
    finally:
        conn.close()


if __name__ == "__main__":
    run_schema_file()
