from models import models

from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.orm import Session

from fastapi import HTTPException, status


def create_user(avatar: str, name: str, session_id: str, db: Session):
    try:
        user = models.User(name=name, avatar=avatar, session_id=session_id)
        db.add(user)
        # db.commit()
    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User for this session already exists.",
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return user


def create_room(name: str, password: str, user: models.User, db: Session):
    try:
        room = models.Room(name=name, password=password)
        db.add(room)
        db.flush()
        a = models.Association(user=user, room=room, usertype=models.UserType.host)
        db.add(a)
        db.commit()
    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Room for this session already exists.",
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return room


def get_user_by_session(session_id: str, db: Session):
    try:
        user: list[models.User] = (
            db.query(models.User).filter(models.User.session_id == session_id).one()
        )
        assert user, "There is no user for this session"
    except AssertionError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except NoResultFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="There is no user for this session",
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return user


def get_room_playlist(room: models.Room, db: Session):
    try:
        queue = (
            db.query(models.Song)
            .filter(
                models.Song.room == room,
                models.Song.status == models.SongState.in_queue,
            )
            .all()
        )
        current: list = (
            db.query(models.Song)
            .filter(
                models.Song.room == room,
                models.Song.status == models.SongState.is_playing,
            )
            .all()
        )
        played = (
            db.query(models.Song)
            .filter(
                models.Song.room == room, models.Song.status == models.SongState.played
            )
            .all()
        )
        playlist = played + current + queue
    except NoResultFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return sorted(playlist, key=lambda x: x.queue_num)
