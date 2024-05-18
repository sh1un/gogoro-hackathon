from secret import get_langchain_api_key, set_environment_variable


def set_up_langsmith() -> None:
    set_environment_variable("LANGCAHIN_API_KEY", get_langchain_api_key())
    set_environment_variable("LANGCHAIN_TRACING_V2", "true")
    set_environment_variable("LANGCHAIN_PROJECT", "gogoro-hackathon")
