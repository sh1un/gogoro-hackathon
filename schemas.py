from typing import List

from langchain_core.pydantic_v1 import BaseModel, Field


class Reflection(BaseModel):
    reflection: str = Field(
        description="A reflection on the answer.",
        example="I think my answer is too verbose.",
    )
