import re
import json
from langchain_core.messages import SystemMessage, HumanMessage
from core.llm import get_llm
from agents.sql_agent import run_sql_agent
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


def create_orchestrator(config=None):
    def run(inputs):
        llm = get_llm(config)
        user_query = inputs["messages"][0].content
        agent_trace = []

        history = [f"User query: {user_query}"]

        for step in range(MAX_STEPS):
            context = "\n\n".join(history)
            context += "\n\nDecide your next action."

            messages = [
                SystemMessage(content=ORCHESTRATOR_PROMPT),
                HumanMessage(content=context),
            ]

            response = llm.invoke(messages)
            raw = response.content.strip()

            agent_trace.append({
                "agent": "orchestrator",
                "action": "decide",
                "content": raw,
                "step": step,
            })

            parsed = _parse_action(raw)

            if parsed["action"] == "sql":
                sql, result = run_sql_agent(parsed.get("request", user_query), config)
                agent_trace.append({
                    "agent": "sql_agent",
                    "action": "query",
                    "content": f"SQL: {sql}\nResult: {result}",
                    "step": step,
                })
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
                    "action": "send",
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
                return {"messages": inputs["messages"], "agent_trace": agent_trace}

            else:
                agent_trace.append({
                    "agent": "orchestrator",
                    "action": "respond",
                    "content": raw,
                    "step": step,
                })
                return {"messages": inputs["messages"], "agent_trace": agent_trace}

        return {"messages": inputs["messages"], "agent_trace": agent_trace}

    return _OrchestratorWrapper(run)


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
