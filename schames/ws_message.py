from pydantic import BaseModel


class WSMessageRequest(BaseModel):
    content: str