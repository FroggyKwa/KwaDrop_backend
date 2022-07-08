from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.orm import Session

from FastApi_sessions.fastapi_session import SessionData, backend, cookie, verifier
from database.db import get_db
from db_methods.db_methods import (
    create_user as db_create_user,
    get_user_by_session,
    create_room as db_create_room,
)
from models import models, schemas
from uuid import UUID, uuid4
from pytube import YouTube

router = APIRouter()


@router.post(
    "/create_user",
    dependencies=[Depends(cookie)],
    response_model=schemas.User,
    tags=["User"],
)
async def create_user(
    name: str,
    session_data: SessionData = Depends(verifier),
    db: Session = Depends(get_db),
):
    try:
        session_id = session_data.dict()["session_id"]
        session_data.username = name
        user = db_create_user(name, session_id, db)
        db.commit()
    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User for this session already exists.",
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return user


@router.patch(
    "/rename_user",
    dependencies=[Depends(cookie)],
    response_model=schemas.User,
    tags=["User"],
)
async def rename_user(
    name: str,
    session_data: SessionData = Depends((verifier)),
    db: Session = Depends(get_db),
):
    try:
        user = get_user_by_session(session_data.session_id, db)
        setattr(user, "name", name)
        db.commit()
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return user


@router.delete(
    "/delete_user",
    dependencies=[Depends(cookie)],
    response_model=schemas.User,
    tags=["User"],
)
async def delete_user(
    session_data: SessionData = Depends((verifier)), db: Session = Depends(get_db)
):
    try:  # todo: если юзер хост - удалаять комнату
        user: models.User = get_user_by_session(session_data.session_id, db)
        try:
            a = (
                db.query(models.Association)
                .filter(models.Association.user == user)
                .one()
            )
            db.delete(a)
        except NoResultFound:
            pass
        db.delete(user)
        db.commit()
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return user


@router.post(
    "/create_room",
    dependencies=[Depends(cookie)],
    response_model=schemas.Room,
    tags=["Room"],
)
async def create_room(
    name: str,
    password: Optional[str] = None,
    session_data: SessionData = Depends(verifier),
    db: Session = Depends(get_db),
):
    try:
        user = get_user_by_session(session_data.session_id, db)
        try:
            a = (
                db.query(models.Association)
                .filter(models.Association.user == user)
                .one()
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User already has association to existing room.",
            )
        except NoResultFound:
            pass
        room = db_create_room(name, password, user, db)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return room


@router.get(
    "/get_roommates",
    dependencies=[Depends(cookie)],
    response_model=schemas.UserList,
    tags=["Room"],
)
async def get_roommates(
    session_data: SessionData = Depends((verifier)), db: Session = Depends(get_db)
):
    try:
        user: models.User = get_user_by_session(session_data.session_id, db)
        a: models.Association = db.query(models.Association).filter(
            models.Association.user == user
        ).one()
        room = db.query(models.Room).filter(models.Room.id == a.room_id).one()
        a_list = (
            db.query(models.Association).filter(models.Association.room == room).all()
        )
    except NoResultFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This user has no association with any room.",
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return schemas.UserList(users=a_list)


@router.patch(
    "/edit_room",
    dependencies=[Depends(cookie)],
    response_model=schemas.Room,
    tags=["Room"],
)
async def edit_room(
    name: Optional[str] = None,
    password: Optional[str] = None,
    session_data: SessionData = Depends(verifier),
    db: Session = Depends(get_db),
):
    try:
        user: models.User = get_user_by_session(session_data.session_id, db)
        a: models.Association = db.query(models.Association).filter(
            models.Association.user == user
        ).one()
        if a.usertype not in (models.UserType.host, models.UserType.moder):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This user has no permission to edit this room.",
            )
        room = db.query(models.Room).filter(models.Room.id == a.room_id).one()
        if name is not None:
            setattr(room, "name", name)
        if password is not None:
            setattr(room, "password", password)
        db.commit()
    except NoResultFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This user has no association with any room.",
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return room


@router.delete(
    "/delete_room",
    dependencies=[Depends(cookie)],
    response_model=schemas.Room,
    tags=["Room"],
)
async def delete_room(
    session_data: SessionData = Depends(verifier), db: Session = Depends(get_db)
):
    try:
        user: models.User = get_user_by_session(session_data.session_id, db)
        a: models.Association = db.query(models.Association).filter(
            models.Association.user == user
        ).one()
        if a.usertype not in (models.UserType.host, models.UserType.moder):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This user has no permission to edit this room.",
            )
        room = db.query(models.Room).filter(models.Room.id == a.room_id).one()
        a_list = (
            db.query(models.Association).filter(models.Association.room == room).all()
        )
        for i in a_list:
            db.delete(i)
        db.flush()
        db.delete(room)
        db.commit()
    except NoResultFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This user has no association with any room.",
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return room


@router.post("/connect", dependencies=[Depends(cookie)], tags=["Room"])
async def connect(
    room_id: int,
    password: Optional[str] = None,
    session_data: SessionData = Depends(verifier),
    db: Session = Depends(get_db),
):
    try:
        user: models.User = get_user_by_session(session_data.session_id, db)
        try:
            a = (
                db.query(models.Association)
                .filter(models.Association.user == user)
                .one()
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User already has association to existing room.",
            )
        except NoResultFound:
            pass
        room = db.query(models.Room).filter(models.Room.id == room_id).one()
        if room.password is not None:
            if password != room.password:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Password is incorrect",
                )
        a = models.Association(user=user, room=room, usertype=models.UserType.basic)
        db.add(a)
        db.commit()
    except NoResultFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This user has no association with any room.",
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return room


@router.delete("/disconnect", dependencies=[Depends(cookie)], tags=["Room"])
async def disconnect(
    session_data: SessionData = Depends(verifier), db: Session = Depends(get_db)
):
    try:
        user: models.User = get_user_by_session(session_data.session_id, db)
        a = db.query(models.Association).filter(models.Association.user == user).one()
        db.delete(a)
        db.commit()
    except NoResultFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This user has no association with any room.",
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return schemas.Success()


@router.post(
    "/add_song",
    dependencies=[Depends(cookie)],
    response_model=schemas.Song,
    tags=["Songs"],
)
async def add_song(
    link: str,
    session_data: SessionData = Depends(verifier),
    db: Session = Depends(get_db),
):
    try:
        user: models.User = get_user_by_session(session_data.session_id, db)
        a = db.query(models.Association).filter(models.Association.user == user).one()
        room = db.query(models.Room).filter(models.Room.id == a.room_id).one()

        yt = YouTube(link)

        song = models.Song(
            user=user,
            link=yt.streams.filter(only_audio=True)[0].url,
            room=room,
            status=models.SongState.in_queue,
        )
        db.add(song)
        db.commit()
    except NoResultFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This user has no association with any room.",
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return song


@router.patch(
    "/playnext",
    dependencies=[Depends(cookie)],
    response_model=schemas.Song,
    tags=["Songs"],
)
async def playnext(
    session_data: SessionData = Depends(verifier), db: Session = Depends(get_db)
):
    try:
        user: models.User = get_user_by_session(session_data.session_id, db)
        a = db.query(models.Association).filter(models.Association.user == user).one()
        room = db.query(models.Room).filter(models.Room.id == a.room_id).one()
        queue = (
            db.query(models.Song)
            .filter(
                models.Song.room == room,
                models.Song.status == models.SongState.in_queue,
            )
            .all()
        )
        current: list = db.query(models.Song).filter(
            models.Song.room == room, models.Song.status == models.SongState.is_playing
        ).all()
        played = (
            db.query(models.Song)
            .filter(
                models.Song.room == room, models.Song.status == models.SongState.played
            )
            .all()
        )
        if not current and not queue and not played:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Playlist is empty."
            )
        if not queue and not played:
            return current[0]
        if not queue:
            for i in played:
                setattr(i, "status", models.SongState.in_queue)
            queue = played
        if current:
            setattr(current[0], "status", models.SongState.played)
        setattr(queue[0], "status", models.SongState.is_playing)
        db.commit()
    except NoResultFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This user has no association with any room.",
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return queue[0]


@router.patch(
    "/playprev",
    dependencies=[Depends(cookie)],
    response_model=schemas.Song,
    tags=["Songs"],
)
async def playprev(
    session_data: SessionData = Depends(verifier), db: Session = Depends(get_db)
):
    try:
        user: models.User = get_user_by_session(session_data.session_id, db)
        a = db.query(models.Association).filter(models.Association.user == user).one()
        room = db.query(models.Room).filter(models.Room.id == a.room_id).one()
        queue = (
            db.query(models.Song)
            .filter(
                models.Song.room == room,
                models.Song.status == models.SongState.in_queue,
            )
            .all()
        )
        current: list = db.query(models.Song).filter(
            models.Song.room == room, models.Song.status == models.SongState.is_playing
        ).all()
        played = (
            db.query(models.Song)
            .filter(
                models.Song.room == room, models.Song.status == models.SongState.played
            )
            .all()
        )
        if not current and not queue and not played:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Playlist is empty."
            )
        if not queue and not played:
            return current[0]
        if current:
            setattr(current[0], "status", models.SongState.in_queue)
        if not played:
            setattr(queue[-1], "status", models.SongState.is_playing)
            db.commit()
            return queue[-1]
        else:
            setattr(played[-1], "status", models.SongState.is_playing)
            db.commit()
            return played[-1]
    except NoResultFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This user has no association with any room.",
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch(
    "/playthis",
    dependencies=[Depends(cookie)],
    response_model=schemas.Song,
    tags=["Songs"],
)
async def playthis(
    song_id: int,
    session_data: SessionData = Depends(verifier),
    db: Session = Depends(get_db),
):
    try:
        user: models.User = get_user_by_session(session_data.session_id, db)
        a = db.query(models.Association).filter(models.Association.user == user).one()
        room = db.query(models.Room).filter(models.Room.id == a.room_id).one()
        try:
            song = (
                db.query(models.Song)
                .filter(models.Song.id == song_id, models.Song.room == room)
                .one()
            )
        except NoResultFound:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"There is no song in this room with id {song_id}.",
            )
        songs = db.query(models.Song).filter(models.Song.room == room).all()
        for i in songs:
            if i.id < song_id:
                setattr(i, "status", models.SongState.played)
            elif i.id > song_id:
                setattr(i, "status", models.SongState.in_queue)
            else:
                setattr(i, "status", models.SongState.is_playing)
        db.commit()
    except NoResultFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This user has no association with any room.",
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete(
    "/delete_song",
    dependencies=[Depends(cookie)],
    response_model=schemas.Song,
    tags=["Songs"],
)
async def delete_song(
    song_id: int,
    session_data: SessionData = Depends(verifier),
    db: Session = Depends(get_db),
):
    try:
        user: models.User = get_user_by_session(session_data.session_id, db)
        a = db.query(models.Association).filter(models.Association.user == user).one()
        room = db.query(models.Room).filter(models.Room.id == a.room_id).one()
        if a.usertype not in (
            models.UserType.host,
            models.UserType.moder,
            models.UserType.basic,
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This user has no permission to perform this action.",
            )
        try:
            song = (
                db.query(models.Song)
                .filter(models.Song.id == song_id, models.Song.room == room)
                .one()
            )
            db.delete(song)
            db.commit()
        except NoResultFound:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"There is no song in this room with id {song_id}.",
            )
    except NoResultFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This user has no association with any room.",
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return song


@router.get(
    "/get_current_song",
    dependencies=[Depends(cookie)],
    response_model=schemas.Song,
    tags=["Songs"],
)
async def get_current_song(
    session_data: SessionData = Depends(verifier), db: Session = Depends(get_db)
):
    try:
        user: models.User = get_user_by_session(session_data.session_id, db)
        a = db.query(models.Association).filter(models.Association.user == user).one()
        room = db.query(models.Room).filter(models.Room.id == a.room_id).one()
        current: list = db.query(models.Song).filter(
            models.Song.room == room, models.Song.status == models.SongState.is_playing
        ).all()
        if not current:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Nothing is playing."
            )
    except NoResultFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This user has no association with any room.",
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return current[0]


@router.post(
    "/get_playlist",
    dependencies=[Depends(cookie)],
    response_model=schemas.Playlist,
    tags=["Songs"],
)
async def get_playlist(
    session_data: SessionData = Depends(verifier), db: Session = Depends(get_db)
):
    try:
        user: models.User = get_user_by_session(session_data.session_id, db)
        a = db.query(models.Association).filter(models.Association.user == user).one()
        room = db.query(models.Room).filter(models.Room.id == a.room_id).one()
        queue = (
            db.query(models.Song)
            .filter(
                models.Song.room == room,
                models.Song.status == models.SongState.in_queue,
            )
            .all()
        )
        current: list = db.query(models.Song).filter(
            models.Song.room == room, models.Song.status == models.SongState.is_playing
        ).all()
        played = (
            db.query(models.Song)
            .filter(
                models.Song.room == room, models.Song.status == models.SongState.played
            )
            .all()
        )
    except NoResultFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This user has no association with any room.",
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    playlist = played + current + queue
    return schemas.Playlist(songs=playlist)


@router.post("/create_session", dependencies=[Depends(cookie)], tags=["Session"])
async def create_session(
    response: Response, session_data: SessionData = Depends(verifier.my_call)
):
    try:
        if session_data is not None:
            return f"session already exists"
        session = uuid4()
        data = SessionData(session_id=str(session))

        await backend.create(session, data)
        cookie.attach_to_response(response, session)

        return f"created session"
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/whoami", dependencies=[Depends(cookie)], tags=["Session"])
async def whoami(session_data: SessionData = Depends(verifier)):
    return session_data


@router.delete("/delete_session", tags=["Session"])
async def del_session(response: Response, session_id: UUID = Depends(cookie)):
    await backend.delete(session_id)
    cookie.delete_from_response(response)
    return "deleted session"
