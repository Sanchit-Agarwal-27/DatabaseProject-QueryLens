import streamlit as st
import pymysql
import os
import time
from dotenv import load_dotenv
import pandas as pd

# Import our project modules
from nl_to_sql.pipeline import generate_sql
from optimizer.plan_capture import capture_plan
from db.validator import ConstraintValidator

load_dotenv()

st.set_page_config(page_title="QueryLens - DBMS Engine", layout="wide")

def get_connection():
    return pymysql.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        database=os.getenv("MYSQL_DATABASE", "querylens_hr"),
        cursorclass=pymysql.cursors.DictCursor
    )

st.title("🔍 QueryLens: NL-to-SQL & Query Execution Plan Visibility")
st.caption("BCSE302L Final Review | MySQL 8.0 (InnoDB) + Ollama Local LLM")

# Quick prompt helper pills
preset = st.radio(
    "Or select a quick benchmark test question:",
    [
        "Custom Query",
        "How many employees were absent in the last 30 days?",
        "Show employees hired after 2022 in the Engineering department",
        "Average net pay per job title"
    ],
    horizontal=True
)

default_text = "" if preset == "Custom Query" else preset
user_question = st.text_input("Enter natural-language question:", value=default_text)

if st.button("Analyze & Execute Query", type="primary"):
    if not user_question.strip():
        st.warning("Please enter a question.")
    else:
        conn = get_connection()
        validator = ConstraintValidator(conn)
        
        with st.spinner("1. Querying local Ollama model..."):
            raw_sql = generate_sql(user_question)
            
        st.subheader("1. SQL Translation & Catalog Validation")
        val_result = validator.validate(raw_sql)
        
        col_sql, col_val = st.columns([2, 1])
        with col_sql:
            st.code(raw_sql, language="sql")
        with col_val:
            if val_result.get("valid"):
                st.success(f"✅ Catalog Check Passed\n\nStatement: {val_result.get('statement_type')}")
                st.info(f"Tables detected: {', '.join(val_result.get('tables_involved', []))}")
            else:
                st.error(f"❌ Rejected: {val_result.get('error')}")

        if val_result.get("valid"):
            st.divider()
            st.subheader("2. DBMS Query Execution Plan & Results")
            col_res, col_plan = st.columns([1, 1])

            # Execute Query & Plan
            with col_res:
                st.markdown("#### Query Output")
                cursor = conn.cursor()
                t0 = time.perf_counter()
                cursor.execute(raw_sql)
                rows = cursor.fetchall()
                exec_time = round((time.perf_counter() - t0) * 1000, 2)
                st.caption(f"⏱ Execution Latency: {exec_time} ms | Rows: {len(rows)}")
                if rows:
                    st.write(pd.DataFrame(rows).to_html(index=False), unsafe_allow_html=True)
                else:
                    st.write("No rows returned.")

            with col_plan:
                st.markdown("#### EXPLAIN Execution Profile")
                plan_info = capture_plan(raw_sql)
                
                # Check if it has parsed summary or raw
                if isinstance(plan_info, dict):
                    st.json(plan_info)
                elif isinstance(plan_info, list):
                    st.table(plan_info)
                else:
                    st.code(str(plan_info))

        conn.close()