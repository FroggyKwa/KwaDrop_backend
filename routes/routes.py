from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.params import Query
from fastapi.responses import HTMLResponse
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
    name: str = Query(..., description="""User name"""),
    session_data: SessionData = Depends(verifier),
    db: Session = Depends(get_db),
):
    """
    Creates a **User** for current session if one is not created yet.

    </br>Returns a **User** object.
    """
    try:
        session_id = session_data.dict()["session_id"]
        db_create_user(name, session_id, db)
        db.commit()
        user = get_user_by_session(session_id, db)
        data = SessionData(username=name, userid=user.id, session_id=session_id)
        await backend.update(session_id=UUID(session_id), data=data)
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
    name: str = Query(..., description="""New name"""),
    session_data: SessionData = Depends((verifier)),
    db: Session = Depends(get_db),
):
    """
    Changes **name** of *current* session's user.

    </br>Returns a **User** object.
    """
    try:
        user = get_user_by_session(session_data.session_id, db)
        setattr(user, "name", name)
        db.commit()
        data = SessionData(username=name, userid=user.id, session_id=session_data.session_id)
        await backend.update(session_id=UUID(session_data.session_id), data=data)

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
    """
    Deletes a *current* session's **User**.

    </br>Returns a **User** object.
    """
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
    name: str = Query(..., description="""Name of the room"""),
    password: Optional[str] = Query(None, description="""Password of the room."""),
    session_data: SessionData = Depends(verifier),
    db: Session = Depends(get_db),
):
    """
    Creates a **Room** for *current* user. User automatically connects to this room and becomes an administrator.

    </br>Returns a **Room** object.

        Note that user can belong to only one room.
    """
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
    """
    Returns a list of **User** objects who are connected to *current* **Room**.

        Note that API understands automatically which room is current user connected to.
    """
    try:
        user: models.User = get_user_by_session(session_data.session_id, db)
        a: models.Association = (
            db.query(models.Association).filter(models.Association.user == user).one()
        )
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
    name: Optional[str] = Query(None, description="""New name"""),
    password: Optional[str] = Query(None, description="""New password"""),
    session_data: SessionData = Depends(verifier),
    db: Session = Depends(get_db),
):
    """
    Edits **Room's** settings if **User** has a permission to do this action.

    If you don't want to change a certain setting, do not include a certain parameter into request body.

    Returns a **Room** object.

        Note that API understands automatically which room is current user connected to.
    """
    try:
        user: models.User = get_user_by_session(session_data.session_id, db)
        a: models.Association = (
            db.query(models.Association).filter(models.Association.user == user).one()
        )
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
    """
    Deletes a **Room** if **User** has a permission to do this action. Automatically disconnects all users from this room.

    Returns a **Room** object.

        Note that API understands automatically which room is current user connected to.
    """
    try:
        user: models.User = get_user_by_session(session_data.session_id, db)
        a: models.Association = (
            db.query(models.Association).filter(models.Association.user == user).one()
        )
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
    room_id: int = Query(..., description="""Room id."""),
    password: Optional[str] = Query(None, description="""Room password"""),
    session_data: SessionData = Depends(verifier),
    db: Session = Depends(get_db),
):
    """
    Connects **User** to **Room**.

    Returns a **Room** object.
    """
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
    """
    Disconnects **User** from a **Room**.

        Note that API understands automatically which room is current user connected to.
    """
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
    link: str = Query(..., description="YouTube link to the music video"),
    session_data: SessionData = Depends(verifier),
    db: Session = Depends(get_db),
):
    """
    Adds a **Song** to the **Room** playlist.

    Returns a **Song** object.

        Note that this method does not play a song. To play a song use /playnext, /playprev or /playthis instead.
    """
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
    """
    Plays next **Song** in the **Room** playlist.

    Returns a currently playing **Song** object.
    """
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
    """
    Plays previous **Song** in the **Room** playlist.

    Returns a currently playing **Song** object.
    """
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
    song_id: int = Query(..., description="""Song id"""),
    session_data: SessionData = Depends(verifier),
    db: Session = Depends(get_db),
):
    """
    Plays a chosen **Song** in the **Room** playlist.

    Returns a currently playing **Song** object.
    """
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
        song = (
            db.query(models.Song)
            .filter(models.Song.room == room, models.Song.id == song_id)
            .one()
        )
        return song
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
    song_id: int = Query(..., description="""Song id"""),
    session_data: SessionData = Depends(verifier),
    db: Session = Depends(get_db),
):
    """
    Deletes a chosen **Song** from the **Room** playlist if **User** has a permission to do this action.

    Returns a deleted **Song** object.
    """
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
    """
    Returns a currently playing **Song** object.
    """
    try:
        user: models.User = get_user_by_session(session_data.session_id, db)
        a = db.query(models.Association).filter(models.Association.user == user).one()
        room = db.query(models.Room).filter(models.Room.id == a.room_id).one()
        current: list = (
            db.query(models.Song)
            .filter(
                models.Song.room == room,
                models.Song.status == models.SongState.is_playing,
            )
            .all()
        )
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
    """
    Returns *current* room playlist as a list of **Song** objects.
    """
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
    """
    Initializes a **Session** if one isn't initialized.
    """
    try:
        if session_data is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=f"session already exists"
            )
        session = uuid4()
        data = SessionData(session_id=str(session))

        await backend.create(session, data)
        cookie.attach_to_response(response, session)

        return f"created session"
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/whoami", dependencies=[Depends(cookie)], tags=["Session"])
async def whoami(session_data: SessionData = Depends(verifier)):
    """
    Returns **Session data** if session exists.
    """
    return session_data


@router.delete("/delete_session", tags=["Session"])
async def del_session(response: Response, session_id: UUID = Depends(cookie)):
    """
    Deletes a **Session** if one exists.
    """
    await backend.delete(session_id)
    cookie.delete_from_response(response)
    return "deleted session"


@router.get("/lets_drink_tea", response_class=HTMLResponse)
async def drink_tea(response: HTMLResponse):
    """
    *You seem tired, aren't you? Let's have a cup of tea and relax...*
    """
    response.status_code = status.HTTP_418_IM_A_TEAPOT
    return response.render("".join(open("tea.html", "r")))
