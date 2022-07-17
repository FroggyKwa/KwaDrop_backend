from typing import Optional

from pydantic import BaseModel

import models.models


class Success(BaseModel):
    status = "ok"


class User(BaseModel):
    id: int
    name: str
    session_id: str
    avatar: Optional[str]

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
    queue_num: int
    title: str
    avatar: Optional[str]
    status: models.models.SongState
    user: User

    class Config:
        orm_mode = True


class Playlist(BaseModel):
    songs: list[Song]

    class Config:
        orm_mode = True


class UserList(BaseModel):
    users: list["RoomAssociation"]

    class Config:
        orm_mode = True


class RoomAssociation(BaseModel):
    user: User
    room: Room
    usertype: models.models.UserType

    class Config:
        orm_mode = True


UserList.update_forward_refs()
User.update_forward_refs()
