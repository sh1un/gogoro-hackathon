from langchain_community.chat_message_histories import DynamoDBChatMessageHistory
from langchain_core.messages import AIMessage, HumanMessage


def write_messages_to_table(
    question, answer, table_name="session_table", session_id="0"
) -> None:
    history = DynamoDBChatMessageHistory(
        table_name=table_name, session_id=session_id, primary_key_name="session_id"
    )
    history.add_messages([HumanMessage(content=question), AIMessage(content=answer)])


def get_chat_history(table_name="session_table", session_id="0"):
    history = DynamoDBChatMessageHistory(
        table_name=table_name, session_id=session_id, primary_key_name="session_id"
    )
    return history.messages
