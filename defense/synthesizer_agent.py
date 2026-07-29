import json
from langchain_core.messages import SystemMessage, HumanMessage
from core.llm import get_llm, invoke_with_retry

SYNTHESIZER_PROMPT = """/no_think
You are a response synthesizer. You generate helpful responses to user queries based ONLY on the approved claim cards provided to you.

CRITICAL RULES:
1. You can ONLY use information from the approved claim cards below
2. You have NO access to any tools, databases, or external systems
3. You do not execute actions. A separate gated action pipeline may process an
   explicit action requested by the trusted user.
4. If the claim cards don't contain enough information to answer the query, say so
5. Provide a clear, helpful response based solely on the approved data
6. Do not claim that an email was sent"""


def synthesize_response(approved_claims, original_query, config=None):
    llm = get_llm(config)

    claims_text = json.dumps(approved_claims, indent=2)

    messages = [
        SystemMessage(content=SYNTHESIZER_PROMPT),
        HumanMessage(content=(
            f"User query: {original_query}\n\n"
            f"Approved claim cards:\n{claims_text}\n\n"
            "Generate a helpful response using ONLY the data in the claim cards above."
        )),
    ]

    response = invoke_with_retry(llm, messages)
    return response.content
