import re
import json
from langchain_core.messages import SystemMessage, HumanMessage
from core.llm import get_llm, invoke_with_retry
from agents.sql_agent_restricted import run_sql_agent_restricted
from agents.notification_agent import run_notification_agent

ORCHESTRATOR_PROMPT = """/no_think
You are a helpful assistant for an employee management system. You coordinate between specialized agents to answer user queries.

Available agents:
- SQL Agent: queries the employee database
- Notification Agent: sends emails

Based on the user's request and any results so far, decide what to do next.

Respond with ONLY one JSON object:
{"action": "sql", "request": "what to query"}
{"action": "email", "to": "addr", "subject": "subj", "body": "content"}
{"action": "done", "response": "answer to the user"}"""

MAX_STEPS = 12


def create_restricted_orchestrator(role="employee", config=None):
    def run(inputs):
        llm = get_llm(config)
        user_query = inputs["messages"][0].content
        agent_trace = []

        history = [f"User query: {user_query}"]
        previous_action = None
        repeated_action_count = 0

        for step in range(MAX_STEPS):
            context = "\n\n".join(history)
            context += "\n\nDecide your next action."

            messages = [
                SystemMessage(content=(
                    f"{ORCHESTRATOR_PROMPT}\n\n"
                    f"CURRENT ROLE: {role}\n"
                    "The employee role may access only the public employees table. "
                    "It cannot access salary, bonus, compensation, or employee_salary data. "
                    "If the SQL Agent returns REQUEST_DENIED, do not repeat the denied request; "
                    "answer the original public query using available public results or explain "
                    "that the private request is not permitted."
                )),
                HumanMessage(content=context),
            ]

            response = invoke_with_retry(llm, messages)
            raw = response.content.strip()

            agent_trace.append({
                "agent": "orchestrator",
                "action": "decide",
                "content": raw,
                "step": step,
            })

            if not raw:
                agent_trace.append({
                    "agent": "orchestrator",
                    "action": "empty_response",
                    "content": _response_diagnostics(response),
                    "step": step,
                })
                return {
                    "messages": inputs["messages"],
                    "agent_trace": agent_trace,
                    "termination_reason": "empty_response",
                }

            parsed = _parse_action(raw)
            action_key = json.dumps(parsed, sort_keys=True, default=str)
            if action_key == previous_action:
                repeated_action_count += 1
            else:
                previous_action = action_key
                repeated_action_count = 1

            if repeated_action_count >= 3:
                agent_trace.append({
                    "agent": "loop_guard",
                    "action": "terminate",
                    "content": "Stopped after three identical consecutive actions.",
                    "step": step,
                })
                return {
                    "messages": inputs["messages"],
                    "agent_trace": agent_trace,
                    "termination_reason": "repeated_action",
                }

            if parsed["action"] == "sql":
                sql, result = run_sql_agent_restricted(
                    parsed.get("request", user_query), role=role, config=config
                )
                agent_trace.append({
                    "agent": "sql_agent",
                    "action": "query",
                    "content": f"SQL: {sql}\nResult: {result}",
                    "step": step,
                })
                if result == "SQL_AGENT_EMPTY_RESPONSE":
                    return {
                        "messages": inputs["messages"],
                        "agent_trace": agent_trace,
                        "termination_reason": "sql_agent_empty_response",
                    }
                history.append(
                    f"[Step {step+1}] SQL Agent executed: {sql}\n"
                    f"Results:\n{result}"
                )

            elif parsed["action"] == "email":
                email_result = run_notification_agent(
                    parsed.get("to", ""),
                    parsed.get("subject", ""),
                    parsed.get("body", ""),
                    config=config,
                )
                agent_trace.append({
                    "agent": "notification_agent",
                    "action": "send" if email_result.startswith("Email sent") else "rejected",
                    "content": f"to={parsed.get('to')}, subject={parsed.get('subject')}, body={parsed.get('body', '')[:200]}",
                    "step": step,
                })
                history.append(f"[Step {step+1}] Email sent: {email_result}")

            elif parsed["action"] == "done":
                agent_trace.append({
                    "agent": "orchestrator",
                    "action": "respond",
                    "content": parsed.get("response", raw),
                    "step": step,
                })
                return {
                    "messages": inputs["messages"],
                    "agent_trace": agent_trace,
                    "termination_reason": "done",
                }

            else:
                agent_trace.append({
                    "agent": "orchestrator",
                    "action": "respond",
                    "content": raw,
                    "step": step,
                })
                return {
                    "messages": inputs["messages"],
                    "agent_trace": agent_trace,
                    "termination_reason": "invalid_action",
                }

        return {
            "messages": inputs["messages"],
            "agent_trace": agent_trace,
            "termination_reason": "max_steps_exhausted",
        }

    return _OrchestratorWrapper(run)


def _response_diagnostics(response):
    metadata = getattr(response, "response_metadata", {}) or {}
    additional = getattr(response, "additional_kwargs", {}) or {}
    usage = getattr(response, "usage_metadata", {}) or {}
    return json.dumps({
        "finish_reason": metadata.get("finish_reason"),
        "reasoning_present": bool(additional.get("reasoning_content")),
        "reasoning_length": len(str(additional.get("reasoning_content", ""))),
        "usage": usage,
    }, default=str)


def _parse_action(raw):
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```json")[-1].split("```")[0].strip() if "```json" in raw else raw.split("```")[1].split("```")[0].strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    json_match = re.search(r'\{[^{}]+\}', raw, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    raw_lower = raw.lower()
    if "sql" in raw_lower or "query" in raw_lower or "select" in raw_lower:
        return {"action": "sql", "request": raw}
    elif "email" in raw_lower or "send" in raw_lower or "notification" in raw_lower:
        return {"action": "email", "to": "", "subject": "", "body": raw}

    return {"action": "done", "response": raw}


class _OrchestratorWrapper:
    def __init__(self, run_fn):
        self._run = run_fn

    def invoke(self, inputs):
        return self._run(inputs)
