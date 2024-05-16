from dotenv import load_dotenv
from langchain_aws import ChatBedrock
from langchain_core.agents import AgentFinish
from langgraph.graph import END, StateGraph

from nodes import execute_tools, run_agent_reasoning_engine
from state import AgentState

AGENT_REASON = "agent_reason"
ACT = "act"

load_dotenv()


def should_continue(state: AgentState) -> str:
    if isinstance(state["agent_outcome"], AgentFinish):
        return END
    return ACT


flow = StateGraph(AgentState)
flow.add_node(key=AGENT_REASON, action=run_agent_reasoning_engine)
flow.set_entry_point(key=AGENT_REASON)
flow.add_node(key=ACT, action=execute_tools)
flow.add_conditional_edges(source=AGENT_REASON, path=should_continue)
flow.add_edge(start_key=ACT, end_key=AGENT_REASON)

app = flow.compile()
app.get_graph().draw_mermaid_png(output_file_path="graph.png")

if __name__ == "__main__":
    print("Hello, World!")
    res = app.invoke(
        input={"input": "What is the weather in SF? Write it and triple it."}
    )
    print(res)
