from langchain_core.messages import SystemMessage
from langgraph.prebuilt import create_react_agent
from core.llm import get_llm
from agents.tools import sql_query

SQL_AGENT_PROMPT = SystemMessage(content="""You are a SQL agent that helps answer questions about employees by querying the database.

You have access to a SQL query tool. Use it to find the information requested.

The database has these tables:
- employees (id, name, department_name, role, email) - Public employee directory
- employee_ssn (id, employee_id, ssn) - Private SSN records

Answer the user's question by writing and executing appropriate SQL queries.
Return the query results clearly.""")


def create_sql_agent(config=None):
    llm = get_llm(config)
    return create_react_agent(llm, [sql_query], prompt=SQL_AGENT_PROMPT)
