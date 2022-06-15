from typing import Optional

from pydantic import BaseModel


class SessionData(BaseModel):
    name: Optional[str]
    connected_room_id: Optional[int]
