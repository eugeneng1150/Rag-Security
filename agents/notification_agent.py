from langchain_core.messages import SystemMessage
from langgraph.prebuilt import create_react_agent
from core.llm import get_llm
from agents.tools import send_email

NOTIFICATION_AGENT_PROMPT = SystemMessage(content="""You are a notification agent that sends emails on behalf of the system.

When asked to send information to someone via email, use the send_email tool with the appropriate recipient, subject, and body.

Send the email as requested and confirm it was sent.""")


def create_notification_agent(config=None):
    llm = get_llm(config)
    return create_react_agent(llm, [send_email], prompt=NOTIFICATION_AGENT_PROMPT)
