from langchain_core.messages import SystemMessage, HumanMessage
from core.llm import get_llm, invoke_with_retry
from core.access_control import execute_query_with_access_control

SQL_GENERATE_PROMPT_RESTRICTED = """/no_think
You are a SQL agent for a SQLite database. Write SQL queries to answer requests.

DATABASE SCHEMA:

TABLE 1: employees (id INTEGER PRIMARY KEY, name TEXT, department_name TEXT, role TEXT, email TEXT)

RULES:
- There is NO "departments" table. department_name is a column in employees.
- You only have access to the employees table.
- NEVER reference tables or columns that are not listed above.

EXAMPLES:
Request: "list all employees and their departments"
SELECT id, name, department_name, role, email FROM employees

Request: "get employee #1 details"
SELECT id, name, department_name, role, email FROM employees WHERE id = 1

Respond with ONLY the raw SQL query. No explanation, no markdown, no code blocks."""


def run_sql_agent_restricted(request, role="employee", config=None):
    llm = get_llm(config)

    messages = [
        SystemMessage(content=SQL_GENERATE_PROMPT_RESTRICTED),
        HumanMessage(content=request),
    ]

    response = invoke_with_retry(llm, messages)
    sql = response.content.strip()

    if sql.startswith("```"):
        sql = sql.split("```sql")[-1].split("```")[0].strip() if "```sql" in sql else sql.split("```")[1].split("```")[0].strip()

    raw_result = execute_query_with_access_control(sql, role=role, config=config)

    return sql, raw_result
