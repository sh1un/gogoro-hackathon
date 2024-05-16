from dotenv import load_dotenv
from langgraph.prebuilt import ToolExecutor

from react import react_agent_runnable, tools
from state import AgentState

load_dotenv()


def run_agent_reasoning_engine(state: AgentState) -> dict:
    agent_outcome = react_agent_runnable.invoke(state)

    return {"agent_outcome": agent_outcome}


tool_executor = ToolExecutor(tools)


def execute_tools(state: AgentState):
    agent_action = state["agent_outcome"]
    output = tool_executor.invoke(agent_action)

    return {"intermediate_steps": [(agent_action, output)]}
