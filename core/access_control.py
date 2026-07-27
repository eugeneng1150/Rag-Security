import re

ROLE_PERMISSIONS = {
    "employee": {"employees"},
    "finance": {"employees", "employee_salary"},
}

_TABLE_PATTERN = re.compile(
    r"\b(FROM|JOIN|INTO|UPDATE|TABLE)\s+(\w+)", re.IGNORECASE
)
_WRITE_OR_ADMIN_PATTERN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|REPLACE|ATTACH|DETACH|PRAGMA|VACUUM|REINDEX)\b",
    re.IGNORECASE,
)


def check_sql_policy(sql, role="employee"):
    """Allow a single, read-only SELECT against role-authorized tables.

    This intentionally accepts only the small SQL subset needed by the
    experiments. It prevents LLM-generated database mutation and removes the
    need to infer intent from a natural-language prompt.
    """
    statement = (sql or "").strip()
    if not statement:
        return False, "empty SQL query"
    if "--" in statement or "/*" in statement or "*/" in statement:
        return False, "SQL comments are not allowed"
    if statement.endswith(";"):
        statement = statement[:-1].strip()
    if ";" in statement:
        return False, "multiple SQL statements are not allowed"
    if not statement.upper().startswith("SELECT"):
        return False, "only SELECT queries are allowed"
    if _WRITE_OR_ADMIN_PATTERN.search(statement):
        return False, "write or administrative SQL is not allowed"

    allowed, denied = check_sql_access(statement, role)
    if not allowed:
        return False, f"role '{role}' cannot access: {', '.join(sorted(denied))}"
    return True, ""


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

    allowed, reason = check_sql_policy(sql, role)
    if not allowed:
        return f"ACCESS DENIED: {reason}"
    return execute_query(sql, config, role=role)
