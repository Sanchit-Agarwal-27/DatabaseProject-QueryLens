# db/transactions.py
import json
import pymysql

class TransactionManager:
    """
    ACID Transaction Engine with Before/After JSON Image Logging & Undo.
    """
    def __init__(self, connection):
        self.conn = connection

    def execute_logged_write(self, question: str, sql: str, table_name: str, primary_key: str, pk_value) -> dict:
        cursor = self.conn.cursor()
        try:
            # 1. START TRANSACTION
            self.conn.begin()
            
            # 2. Capture BEFORE-IMAGE
            cursor.execute(f"SELECT * FROM {table_name} WHERE {primary_key} = %s FOR UPDATE;", (pk_value,))
            before_row = cursor.fetchone()
            before_json = json.dumps(before_row, default=str) if before_row else None
            
            # 3. Execute write
            cursor.execute(sql)
            
            # 4. Capture AFTER-IMAGE
            cursor.execute(f"SELECT * FROM {table_name} WHERE {primary_key} = %s;", (pk_value,))
            after_row = cursor.fetchone()
            after_json = json.dumps(after_row, default=str) if after_row else None
            
            # 5. Write to query_log
            action = sql.strip().split()[0].upper()
            cursor.execute("""
                INSERT INTO query_log (question, sql_text, target_table, before_image, after_image, action_type, status)
                VALUES (%s, %s, %s, %s, %s, %s, 'COMMITTED');
            """, (question, sql, table_name, before_json, after_json, action))
            
            # 6. COMMIT
            self.conn.commit()
            return {"status": "SUCCESS", "message": "Transaction committed and logged."}
            
        except Exception as e:
            self.conn.rollback()
            return {"status": "ROLLED_BACK", "error": str(e)}

    def undo_last_write(self) -> dict:
        """Reads latest committed log and restores before_image."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM query_log WHERE status = 'COMMITTED' ORDER BY log_id DESC LIMIT 1;")
        entry = cursor.fetchone()
        if not entry:
            return {"status": "ERROR", "message": "No committed operations to undo."}
            
        target_table = entry["target_table"] if isinstance(entry, dict) else entry[3]
        before_raw = entry["before_image"] if isinstance(entry, dict) else entry[4]
        log_id = entry["log_id"] if isinstance(entry, dict) else entry[0]
        
        if not before_raw:
            return {"status": "ERROR", "message": "No before-image exists (row was newly created)."}
            
        before_data = json.loads(before_raw) if isinstance(before_raw, str) else before_raw
        
        # Build UPDATE to restore prior values
        set_clauses = [f"{k} = %s" for k in before_data.keys()]
        values = list(before_data.values())
        
        # Use first key as primary key
        pk_col = list(before_data.keys())[0]
        pk_val = before_data[pk_col]
        values.append(pk_val)
        
        restore_sql = f"UPDATE {target_table} SET {', '.join(set_clauses)} WHERE {pk_col} = %s;"
        
        try:
            self.conn.begin()
            cursor.execute(restore_sql, values)
            cursor.execute("UPDATE query_log SET status = 'UNDONE' WHERE log_id = %s;", (log_id,))
            self.conn.commit()
            return {"status": "SUCCESS", "message": f"Undid log entry #{log_id}. Restored original record state."}
        except Exception as e:
            self.conn.rollback()
            return {"status": "FAILED", "error": str(e)}