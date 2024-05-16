from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

actor_prompt_template = ChatPromptTemplate(
    [
        (
            "system",
            """You are expert researcher.
      Current time: {time}
      1. {first_instruction}
      2. Reflect and critique your answer. Be severe to maximize improvement.
      3. Recommend search queries to improve your answer.
      """,
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
).partial()
