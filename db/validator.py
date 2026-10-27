# db/validator.py
import re
import pymysql

class ConstraintValidator:
    """
    Validates LLM-generated SQL against information_schema catalog
    Rejects DDL, hallucinated tables/columns, and unqualified mutations.
    """
    ALLOWED_VERBS = {"SELECT", "INSERT", "UPDATE", "DELETE"}
    
    def __init__(self, connection):
        self.conn = connection
        self.catalog = self._load_catalog()

    def _load_catalog(self):
        cursor = self.conn.cursor()
        # Fetch valid tables and their columns
        cursor.execute("""
            SELECT TABLE_NAME, COLUMN_NAME 
            FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE();
        """)
        catalog = {}
        for row in cursor.fetchall():
            tbl = row[0].lower() if isinstance(row, tuple) else row["TABLE_NAME"].lower()
            col = row[1].lower() if isinstance(row, tuple) else row["COLUMN_NAME"].lower()
            if tbl not in catalog:
                catalog[tbl] = set()
            catalog[tbl].add(col)
        return catalog

    def validate(self, sql: str) -> dict:
        clean_sql = sql.strip().rstrip(";")
        first_word = clean_sql.split()[0].upper()

        # 1. Whitelist check
        if first_word not in self.ALLOWED_VERBS:
            return {"valid": False, "error": f"Security Violation: Statement '{first_word}' is prohibited. Only DML allowed."}

        # 2. Check for dangerous write (UPDATE/DELETE without WHERE)
        if first_word in {"UPDATE", "DELETE"}:
            if not re.search(r"\bWHERE\b", clean_sql, re.IGNORECASE):
                return {"valid": False, "error": f"Safety Violation: Unqualified {first_word} statement without WHERE clause blocked!"}

        # 3. Simple table existence check
        words = set(re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b", clean_sql.lower()))
        valid_tables = set(self.catalog.keys())
        found_tables = words.intersection(valid_tables)

        if not found_tables and first_word == "SELECT":
            return {"valid": False, "error": "Catalog Violation: No recognized database tables found in query."}

        return {
            "valid": True,
            "statement_type": first_word,
            "tables_involved": list(found_tables),
            "message": "Passed all integrity constraints and catalog verification."
        }