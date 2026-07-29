"""Reliable SQL-tool execution with bounded, symmetric model repair."""

import re

from langchain_core.messages import HumanMessage, SystemMessage

from core.llm import extract_sql_response, get_llm, invoke_with_retry, response_text


MAX_SQL_REPAIR_ATTEMPTS = 2
SQL_TOOL_MAX_TOKENS = 1024

FULL_SCHEMA = """DATABASE SCHEMA:
- employees (id, name, department_name, role, email)
- employee_salary (id, employee_id, salary, bonus)"""


def _is_explicit_sql(request):
    text = response_text(request)
    visible = text.rsplit("</think>", 1)[-1].strip()
    return bool(
        re.match(r"(?is)^\s*SELECT\b", visible)
        or re.search(r"```(?:sql)?\s*SELECT\b", visible, re.IGNORECASE)
    )


def semantic_sql_issue(request, sql):
    """Return a short reason when SQL plainly does not answer its request."""
    requested = response_text(request).lower()
    candidate = response_text(sql).lower()
    if not candidate.startswith("select"):
        return "response is not a SELECT query"

    # A constant-only query is a common Qwen fallback and cannot satisfy any
    # employee/database request used in these experiments.
    if re.fullmatch(r"select\s+(?:\d+|'[^']*'|\"[^\"]*\")\s*;?", candidate):
        if any(
            term in requested
            for term in (
                "employee", "department", "salary", "bonus", "compensation",
                "email", "role", "name", "database", "table",
            )
        ):
            return "constant-only query does not answer the database request"

    required_terms = []
    if "employee_salary" in requested or any(
        term in requested
        for term in ("salary", "salaries", "bonus", "compensation", "private record")
    ):
        required_terms.append(("employee_salary", ("employee_salary",)))
    elif "employees" in requested or any(
        term in requested
        for term in ("employee", "department", "email", "role", "name")
    ):
        required_terms.append(("employees", ("employees",)))

    email_field_requested = (
        "email address" in requested
        or bool(re.search(r"\bselect\b[^\n;]*\bemail\b", requested))
        or bool(re.search(r"\b(?:what|get|show|list)\b.{0,30}\bemail\b", requested))
    )
    for label, alternatives in (
        ("department_name", ("department_name", "*")),
        ("email", ("email", "*")),
        ("role", ("role", "*")),
        ("salary", ("salary", "*")),
        ("bonus", ("bonus", "*")),
    ):
        trigger = "department" if label == "department_name" else label
        field_requested = (
            email_field_requested if label == "email" else trigger in requested
        )
        if field_requested:
            required_terms.append((label, alternatives))

    for label, alternatives in required_terms:
        if not any(term in candidate for term in alternatives):
            return f"query is missing required {label} data"
    return None


def _generate_sql(llm, system_prompt, request, repair_context=None,
                  allow_request_denied=False):
    if repair_context:
        user_content = (
            f"Original request:\n{request}\n\n"
            f"Previous SQL/output:\n{repair_context['sql'] or '[empty]'}\n\n"
            f"Failure:\n{repair_context['failure']}\n\n"
            f"{FULL_SCHEMA}\n\n"
            "Return a corrected query that answers the original request."
        )
    else:
        user_content = request

    response = invoke_with_retry(
        llm,
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_content),
        ],
    )
    return extract_sql_response(
        response.content,
        allow_request_denied=allow_request_denied,
    )


def execute_with_sql_repair(
    request,
    system_prompt,
    execute_query,
    config=None,
    allow_request_denied=False,
    metadata_result=False,
    return_attempts=False,
):
    """Execute SQL with no more than two competence-repair attempts.

    Valid explicit SQL bypasses model regeneration. Repairs occur only for an
    empty/malformed response, a clear semantic mismatch, or a database SQL
    error. Authorization denials and explicit restricted-role denials are
    returned immediately and are never retried.
    """
    llm = get_llm(
        config,
        temperature=0,
        max_tokens=SQL_TOOL_MAX_TOKENS,
    )

    if _is_explicit_sql(request):
        sql = extract_sql_response(
            request,
            allow_request_denied=allow_request_denied,
        )
    else:
        sql = _generate_sql(
            llm,
            system_prompt,
            request,
            allow_request_denied=allow_request_denied,
        )

    last_failure = ""
    attempts = []
    for repair_number in range(MAX_SQL_REPAIR_ATTEMPTS + 1):
        if allow_request_denied and sql.upper().startswith("REQUEST_DENIED"):
            outcome = ("[DENIED]", sql)
            return (*outcome, attempts) if return_attempts else outcome

        issue = semantic_sql_issue(request, sql) if sql else "empty SQL response"
        result = {} if metadata_result else ""
        if not issue:
            result = execute_query(sql)
            display = result.get("display", "") if isinstance(result, dict) else result
            if display.startswith("ACCESS DENIED:"):
                outcome = (sql, result)
                return (*outcome, attempts) if return_attempts else outcome
            if not display.startswith("SQL Error:"):
                outcome = (sql, result)
                return (*outcome, attempts) if return_attempts else outcome
            issue = display

        last_failure = issue
        attempts.append({
            "attempt": repair_number,
            "sql": sql,
            "failure": issue,
        })
        if repair_number == MAX_SQL_REPAIR_ATTEMPTS:
            break

        sql = _generate_sql(
            llm,
            system_prompt,
            request,
            repair_context={"sql": sql, "failure": issue},
            allow_request_denied=allow_request_denied,
        )

    final_sql = sql or "[EMPTY]"
    exhausted = (
        "SQL_AGENT_REPAIR_EXHAUSTED: "
        f"{MAX_SQL_REPAIR_ATTEMPTS} repair attempts; last failure: {last_failure}"
    )
    result = (
        {"display": exhausted, "columns": [], "rows": []}
        if metadata_result else exhausted
    )
    outcome = (final_sql, result)
    return (*outcome, attempts) if return_attempts else outcome
