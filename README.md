# QueryLens (local Ollama edition)

NL-to-SQL with a local LLM, plus real database engineering underneath:
EXPLAIN plans, indexing benchmarks, a heuristic optimizer, constraint
validation, and transaction logging. No API keys anywhere.

## Setup (do in order, stop if a step fails)

1. **Install Ollama** from https://ollama.com/download and open it.
2. **Download a model** (once, ~4-5 GB):
   ```
   ollama pull qwen2.5-coder:7b
   ```
   Low on RAM (8 GB or less)? Use `ollama pull qwen2.5-coder:3b` and set
   `OLLAMA_MODEL=qwen2.5-coder:3b` in `.env`.
3. **Install Python deps** (inside the querylens folder):
   ```
   pip install -r requirements.txt
   ```
4. **Create `.env`**: `copy .env.example .env`, then put your MySQL root password in it.
5. **Create schema**: `python -m db.connection`  -> "Schema created successfully."
6. **Generate data**: `python -m db.generate_data` -> "Done. Data generation complete."
7. **Test the LLM alone**: `python -m nl_to_sql.pipeline` -> prints a SQL query.
8. **Test plan capture alone**: `python -m optimizer.plan_capture` -> prints a plan.
9. **Run the dashboard**: `streamlit run app.py`

## Roadmap
- [x] Schema, data, local NL-to-SQL, EXPLAIN capture
- [ ] Indexing + before/after benchmark
- [ ] Heuristic query optimizer
- [ ] Constraint validation
- [ ] Transactions + WAL-style log with undo
- [ ] Dashboard polish + report mapped to syllabus modules
