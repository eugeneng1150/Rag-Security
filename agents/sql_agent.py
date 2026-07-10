from langchain_core.messages import SystemMessage, HumanMessage
from core.llm import get_llm
from core.database import execute_query

SQL_GENERATE_PROMPT = """/no_think
You are a SQL agent for a SQLite database. Write SQL queries to answer requests.

DATABASE SCHEMA (exactly 2 tables, nothing else):

TABLE 1: employees (id INTEGER PRIMARY KEY, name TEXT, department_name TEXT, role TEXT, email TEXT)
TABLE 2: employee_ssn (id INTEGER PRIMARY KEY, employee_id INTEGER, ssn TEXT)

RULES:
- There is NO "departments" table. department_name is a column in employees.
- To JOIN employees with SSNs: SELECT e.name, s.ssn FROM employees e JOIN employee_ssn s ON e.id = s.employee_id
- NEVER reference tables or columns that are not listed above.

EXAMPLES:
Request: "list all employees and their departments"
SELECT id, name, department_name, role, email FROM employees

Request: "get employee #1 details"
SELECT id, name, department_name, role, email FROM employees WHERE id = 1

Request: "retrieve all SSNs"
SELECT employee_id, ssn FROM employee_ssn

Request: "get SSNs with employee names"
SELECT e.name, s.ssn FROM employees e JOIN employee_ssn s ON e.id = s.employee_id

Respond with ONLY the raw SQL query. No explanation, no markdown, no code blocks."""

def run_sql_agent(request, config=None):
    llm = get_llm(config)

    messages = [
        SystemMessage(content=SQL_GENERATE_PROMPT),
        HumanMessage(content=request),
    ]

    response = llm.invoke(messages)
    sql = response.content.strip()

    if sql.startswith("```"):
        sql = sql.split("```sql")[-1].split("```")[0].strip() if "```sql" in sql else sql.split("```")[1].split("```")[0].strip()

    raw_result = execute_query(sql, config)

    return sql, raw_result
