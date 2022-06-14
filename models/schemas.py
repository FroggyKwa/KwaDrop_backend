from pydantic import BaseModel
from typing import Optional


class Success(BaseModel):
    status = "ok"


class User(BaseModel):
    name: str
    session_id: str

    class Config:
        orm_mode = True