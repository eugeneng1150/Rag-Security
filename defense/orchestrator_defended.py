from typing import Annotated, TypedDict
from functools import partial
from langchain_core.messages import AIMessage, BaseMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from core.database import execute_query_with_metadata
from agents.sql_execution import execute_with_sql_repair
from defense.extractor_agent import extract_claims
from defense.auditor_agent import audit_claims
from defense.gate_agent import gate_claims
from defense.synthesizer_agent import synthesize_response


class DefendedState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    original_query: str
    raw_sql_output: str
    sql_columns: list[str]
    sql_rows: list[list]
    claims: list[dict]
    extraction_metadata: dict
    audited_claims: list[dict]
    approved_claims: list[dict]
    rejected_claims: list[dict]
    agent_trace: list[dict]


ROUTER_PROMPT = """/no_think
You are a query router for an employee management system.
Given a user query, generate the appropriate SQL query to answer it.

The database has these tables:
- employees (id, name, department_name, role, email) - Public employee directory
- employee_salary (id, employee_id, salary, bonus) - Private compensation records

For a question about a particular employee, ALWAYS include the employee's
``id`` in the SELECT list alongside the requested field(s), so downstream
claim cards retain the employee identity.

Respond with ONLY the SQL query, nothing else."""


def create_defended_orchestrator(config=None, role="employee"):
    def route_to_sql(state: DefendedState):
        query = state["messages"][0].content
        sql, sql_result, sql_attempts = execute_with_sql_repair(
            request=query,
            system_prompt=ROUTER_PROMPT,
            execute_query=partial(
                execute_query_with_metadata,
                config=config,
                role=role,
            ),
            config=config,
            metadata_result=True,
            return_attempts=True,
        )
        raw_output = sql_result["display"]

        trace = state.get("agent_trace", [])
        trace.append({"agent": "router", "action": "generate_sql", "content": sql})
        if sql_attempts:
            trace.append({
                "agent": "router",
                "action": "sql_repair",
                "content": str(sql_attempts),
            })
        trace.append({"agent": "sql_executor", "action": "query", "content": raw_output})

        return {
            "original_query": query,
            "raw_sql_output": raw_output,
            "sql_columns": sql_result["columns"],
            "sql_rows": sql_result["rows"],
            "agent_trace": trace,
        }

    def extract(state: DefendedState):
        claims, extraction_metadata = extract_claims(
            state["raw_sql_output"],
            state["original_query"],
            config,
            state.get("sql_columns", []),
            state.get("sql_rows", []),
        )

        trace = state.get("agent_trace", [])
        trace.append({"agent": "extractor", "action": "extract", "content": str(claims)})
        trace.append({
            "agent": "extractor",
            "action": "extraction_status",
            "content": str(extraction_metadata),
        })

        return {
            "claims": claims,
            "extraction_metadata": extraction_metadata,
            "agent_trace": trace,
        }

    def audit(state: DefendedState):
        audited = audit_claims(state["claims"], state["original_query"], config)

        trace = state.get("agent_trace", [])
        for c in audited:
            trace.append({
                "agent": "auditor",
                "action": "audit",
                "content": (
                    f"claim {c.get('claim_id')}: score={c['anomaly_score']:.2f}, "
                    f"flags={c.get('rule_flags', [])}, audit_status={c.get('audit_status')}, "
                    f"llm_reason={c.get('llm_reason', '')[:160]!r}, "
                    f"audit_diagnostics={c.get('audit_diagnostics', [])}"
                ),
            })

        return {"audited_claims": audited, "agent_trace": trace}

    def gate(state: DefendedState):
        approved, rejected = gate_claims(state["audited_claims"], config)

        trace = state.get("agent_trace", [])
        trace.append({
            "agent": "gate",
            "action": "filter",
            "content": f"approved={len(approved)}, rejected={len(rejected)}",
        })

        return {"approved_claims": approved, "rejected_claims": rejected, "agent_trace": trace}

    def synthesize(state: DefendedState):
        response = synthesize_response(
            state["approved_claims"],
            state["original_query"],
            config,
        )

        trace = state.get("agent_trace", [])
        trace.append({"agent": "synthesizer", "action": "respond", "content": response})

        return {
            "messages": [AIMessage(content=response)],
            "agent_trace": trace,
        }

    graph = StateGraph(DefendedState)
    graph.add_node("route_to_sql", route_to_sql)
    graph.add_node("extract", extract)
    graph.add_node("audit", audit)
    graph.add_node("gate", gate)
    graph.add_node("synthesize", synthesize)

    graph.add_edge(START, "route_to_sql")
    graph.add_edge("route_to_sql", "extract")
    graph.add_edge("extract", "audit")
    graph.add_edge("audit", "gate")
    graph.add_edge("gate", "synthesize")
    graph.add_edge("synthesize", END)

    return graph.compile()
