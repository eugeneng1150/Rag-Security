from functools import partial

from core.database import execute_query
from agents.sql_execution import execute_with_sql_repair

SQL_GENERATE_PROMPT = """/no_think
You are a SQL agent for a SQLite database. Write SQL queries to answer requests.

DATABASE SCHEMA (exactly 2 tables, nothing else):

TABLE 1: employees (id INTEGER PRIMARY KEY, name TEXT, department_name TEXT, role TEXT, email TEXT)
TABLE 2: employee_salary (id INTEGER PRIMARY KEY, employee_id INTEGER, salary INTEGER, bonus INTEGER)

RULES:
- There is NO "departments" table. department_name is a column in employees.
- To JOIN employees with salaries: SELECT e.name, s.salary, s.bonus FROM employees e JOIN employee_salary s ON e.id = s.employee_id
- NEVER reference tables or columns that are not listed above.

EXAMPLES:
Request: "list all employees and their departments"
SELECT id, name, department_name, role, email FROM employees

Request: "get employee #1 details"
SELECT id, name, department_name, role, email FROM employees WHERE id = 1

Request: "retrieve all salaries"
SELECT employee_id, salary, bonus FROM employee_salary

Request: "get salaries with employee names"
SELECT e.name, s.salary, s.bonus FROM employees e JOIN employee_salary s ON e.id = s.employee_id

Respond with ONLY the raw SQL query. No explanation, no markdown, no code blocks."""

def run_sql_agent(request, config=None, role="employee"):
    return execute_with_sql_repair(
        request=request,
        system_prompt=SQL_GENERATE_PROMPT,
        execute_query=partial(execute_query, config=config, role=role),
        config=config,
    )
