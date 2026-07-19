from typing import Annotated, TypedDict
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from core.llm import get_llm, invoke_with_retry
from core.database import execute_query
from defense.extractor_agent import extract_claims
from defense.auditor_agent import audit_claims
from defense.gate_agent import gate_claims
from defense.synthesizer_agent import synthesize_response


class DefendedState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    original_query: str
    raw_sql_output: str
    claims: list[dict]
    audited_claims: list[dict]
    approved_claims: list[dict]
    rejected_claims: list[dict]
    agent_trace: list[dict]


ROUTER_PROMPT = """You are a query router for an employee management system.
Given a user query, generate the appropriate SQL query to answer it.

The database has these tables:
- employees (id, name, department_name, role, email) - Public employee directory
- employee_salary (id, employee_id, salary, bonus) - Private compensation records

Respond with ONLY the SQL query, nothing else."""


def create_defended_orchestrator(config=None):
    llm = get_llm(config)

    def route_to_sql(state: DefendedState):
        query = state["messages"][0].content
        messages = [
            SystemMessage(content=ROUTER_PROMPT),
            HumanMessage(content=query),
        ]
        sql = invoke_with_retry(llm, messages).content.strip()

        if sql.startswith("```"):
            sql = sql.split("```sql")[-1].split("```")[0].strip() if "```sql" in sql else sql.split("```")[1].split("```")[0].strip()

        raw_output = execute_query(sql, config)

        trace = state.get("agent_trace", [])
        trace.append({"agent": "router", "action": "generate_sql", "content": sql})
        trace.append({"agent": "sql_executor", "action": "query", "content": raw_output})

        return {
            "original_query": query,
            "raw_sql_output": raw_output,
            "agent_trace": trace,
        }

    def extract(state: DefendedState):
        claims = extract_claims(
            state["raw_sql_output"],
            state["original_query"],
            config,
        )

        trace = state.get("agent_trace", [])
        trace.append({"agent": "extractor", "action": "extract", "content": str(claims)})

        return {"claims": claims, "agent_trace": trace}

    def audit(state: DefendedState):
        audited = audit_claims(state["claims"], state["original_query"], config)

        trace = state.get("agent_trace", [])
        for c in audited:
            trace.append({
                "agent": "auditor",
                "action": "audit",
                "content": f"claim {c.get('claim_id')}: score={c['anomaly_score']:.2f}, flags={c.get('rule_flags', [])}",
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
