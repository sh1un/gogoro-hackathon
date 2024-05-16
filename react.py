from dotenv import load_dotenv
from langchain import hub
from langchain.agents import create_react_agent
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import tool

from llm import get_model

load_dotenv()

react_prompt: PromptTemplate = hub.pull("hwchase17/react")


@tool
def triple(num: float) -> float:
    """
    Returns the triple of the given number.

    Parameters:
    num (float): The number to be tripled.

    Returns:
    float: The triple of the given number.
    """
    return float(num) * 3


tools = [TavilySearchResults(max_results=1), triple]

react_agent_runnable = create_react_agent(
    llm=get_model(), tools=tools, prompt=react_prompt
)
if __name__ == "__main__":
    llm = get_model()

    print(react_prompt)
