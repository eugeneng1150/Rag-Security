from functools import partial

from core.access_control import execute_query_with_access_control
from agents.sql_execution import execute_with_sql_repair

SQL_GENERATE_PROMPT_RESTRICTED = """/no_think
You are a SQL agent for a SQLite database. Write SQL queries to answer requests.

DATABASE SCHEMA:

TABLE 1: employees (id INTEGER PRIMARY KEY, name TEXT, department_name TEXT, role TEXT, email TEXT)

RULES:
- There is NO "departments" table. department_name is a column in employees.
- You only have access to the employees table.
- NEVER reference tables or columns that are not listed above.
- If the request asks for unavailable or private data such as salary, bonus,
  compensation, or employee_salary, do NOT substitute a different query.
  Respond exactly: REQUEST_DENIED: employee role cannot access private compensation data

EXAMPLES:
Request: "list all employees and their departments"
SELECT id, name, department_name, role, email FROM employees

Request: "get employee #1 details"
SELECT id, name, department_name, role, email FROM employees WHERE id = 1

Respond with either the raw SQL query or the exact REQUEST_DENIED line. No
explanation, markdown, or code blocks."""


def run_sql_agent_restricted(request, role="employee", config=None):
    return execute_with_sql_repair(
        request=request,
        system_prompt=SQL_GENERATE_PROMPT_RESTRICTED,
        execute_query=partial(
            execute_query_with_access_control,
            role=role,
            config=config,
        ),
        config=config,
        allow_request_denied=True,
    )
