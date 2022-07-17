import enum

from sqlalchemy import Column, Integer, String, ForeignKey, Enum
from sqlalchemy.orm import relationship
import sqlalchemy.orm.collections

from database.db import Base


class UserType(enum.IntEnum):
    host = 0
    moder = 1
    basic = 2
    banned = 3


class SongState(enum.IntEnum):
    in_queue = 0
    is_playing = 1
    played = 2


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    avatar = Column(String)
    name = Column(String, nullable=False)
    session_id = Column(String, nullable=False, unique=True)

    associations = relationship("Association", back_populates="user")


class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    password = Column(String)

    associations = relationship("Association", back_populates="room")


class Association(Base):
    __tablename__ = "associations"

    user_id = Column(ForeignKey("users.id"), primary_key=True)
    room_id = Column(ForeignKey("rooms.id"), primary_key=True)
    usertype = Column(Enum(UserType), default=UserType.basic)

    user = relationship("User", back_populates="associations")
    room = relationship("Room", back_populates="associations")


class Song(Base):
    __tablename__ = "songs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    link = Column(String, nullable=False)
    status = Column(Enum(SongState), default=SongState.in_queue)
    queue_num = Column(Integer, nullable=False)
    title = Column(String)
    avatar = Column(String)
    user_id = Column(ForeignKey("users.id"), primary_key=True)
    room_id = Column(ForeignKey("rooms.id"), primary_key=True)

    user = relationship("User")
    room = relationship("Room")
