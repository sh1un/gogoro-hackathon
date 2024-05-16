from dotenv import load_dotenv
from langchain_aws import ChatBedrock

load_dotenv()


def get_model(model: str = "claude 3 sonnet") -> ChatBedrock:
    model = model.lower()
    if model == "claude 3 sonnet":
        llm = ChatBedrock(
            credentials_profile_name="amb-shiun-bedrock-user",
            model_id="anthropic.claude-3-sonnet-20240229-v1:0",
            streaming=True,
        )

    return llm
