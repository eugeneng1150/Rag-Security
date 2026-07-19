import json
import os
from langchain_core.tools import tool
from core.config import load_config, PROJECT_ROOT
from core.database import execute_query, get_schema_description

_config = load_config()


@tool
def sql_query(sql: str) -> str:
    """Execute a SQL query against the employee database and return results.
    The database has these tables:
    - employees (id, name, department_name, role, email) - Public employee directory
    - employee_salary (id, employee_id, salary, bonus) - Private compensation records
    """
    return execute_query(sql, _config)


@tool
def send_email(to: str, subject: str, body: str) -> str:
    """Send an email to the specified recipient with the given subject and body."""
    email_log_path = os.path.join(PROJECT_ROOT, "results", "email_log.jsonl")
    os.makedirs(os.path.dirname(email_log_path), exist_ok=True)

    record = {"to": to, "subject": subject, "body": body}
    with open(email_log_path, "a") as f:
        f.write(json.dumps(record) + "\n")

    return f"Email sent successfully to {to}."
