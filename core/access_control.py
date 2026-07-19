import re

ROLE_PERMISSIONS = {
    "employee": {"employees"},
    "finance": {"employees", "employee_salary"},
}

_TABLE_PATTERN = re.compile(
    r"\b(FROM|JOIN|INTO|UPDATE|TABLE)\s+(\w+)", re.IGNORECASE
)


def check_sql_access(sql, role="employee"):
    """Check if a SQL query only accesses tables permitted for the given role.

    Returns (allowed, denied_tables). If allowed is False, denied_tables
    lists the table names that the role cannot access.
    """
    allowed_tables = ROLE_PERMISSIONS.get(role, set())
    referenced = {m.group(2).lower() for m in _TABLE_PATTERN.finditer(sql)}
    denied = referenced - allowed_tables
    return len(denied) == 0, denied


def execute_query_with_access_control(sql, role="employee", config=None):
    """Wrapper around execute_query that enforces role-based access control."""
    from core.database import execute_query

    allowed, denied = check_sql_access(sql, role)
    if not allowed:
        return f"ACCESS DENIED: Role '{role}' cannot access table(s): {', '.join(sorted(denied))}"
    return execute_query(sql, config)
