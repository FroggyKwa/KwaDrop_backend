from pydantic import BaseModel
from typing import Optional

import models.models


class Success(BaseModel):
    status = "ok"


class User(BaseModel):
    name: str
    session_id: str

    class Config:
        orm_mode = True


class Room(BaseModel):
    name: str
    id: int

    class Config:
        orm_mode = True


class Song(BaseModel):
    id: int
    link: str
    status: models.models.SongState
    user: User

    class Config:
        orm_mode = True


class Playlist(BaseModel):
    songs: list[Song]

    class Config:
        orm_mode = True
