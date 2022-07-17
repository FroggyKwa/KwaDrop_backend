import json
import secrets
import aiofiles
import os
from typing import Optional

import pytube.exceptions
import requests
from fastapi import APIRouter, Depends, HTTPException, status, Response, UploadFile
from fastapi.params import Query, File
from fastapi.responses import HTMLResponse, FileResponse
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.orm import Session

from FastApi_sessions.fastapi_session import SessionData, backend, cookie, verifier
from database.db import get_db
from db_methods.db_methods import (
    create_user as db_create_user,
    get_user_by_session,
    get_room_playlist,
    create_room as db_create_room,
)
from models import models, schemas
from uuid import UUID, uuid4
from pytube import YouTube

router = APIRouter()


async def save_file(file: UploadFile, out_path: str, max_size=15):
    if file.content_type not in ["image/jpeg", "image/png"]:
        raise HTTPException(status_code=400, detail="Загружать можно только картинки")

    size = 1024
    async with aiofiles.open(out_path, "wb") as out_file:
        content = await file.read(1024 * 1024)
        while content:
            await out_file.write(content)
            content = await file.read(1024 * 1024)
            size += 1024

            if max_size:
                if size / 1024 > max_size:
                    os.unlink(out_path)
                    raise HTTPException(status_code=400, detail="File exceeds max size")


@router.post(
    "/create_user",
    dependencies=[Depends(cookie)],
    response_model=schemas.User,
    tags=["User"],
)
async def create_user(
    name: str = Query(..., description="""User name"""),
    avatar: Optional[UploadFile] = File(None, description="""User avatar"""),
    session_data: SessionData = Depends(verifier),
    db: Session = Depends(get_db),
):
    """
    Creates a **User** for current session if one is not created yet.

    </br>Returns a **User** object.
    """
    try:
        if avatar is not None:
            filename = secrets.token_hex(64) + ".jpg"
            out_path = f"images/{filename}"

            await save_file(avatar, out_path)
        session_id = session_data.dict()["session_id"]
        db_create_user(
            avatar=out_path if avatar is not None else None,
            name=name,
            session_id=session_id,
            db=db,
        )
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
    "/update_avatar",
    dependencies=[Depends(cookie)],
    response_model=schemas.User,
    tags=["User"],
)
async def update_avatar(
    avatar: Optional[UploadFile] = File(None, description="""New avatar"""),
    session_data: SessionData = Depends((verifier)),
    db: Session = Depends(get_db),
):
    """
    Updates or deletes **User** avatar image.

    Returns a **User** object.
    """
    try:
        if avatar is not None:
            filename = secrets.token_hex(64) + ".jpg"
            out_path = f"images/{filename}"

            await save_file(avatar, out_path)
        user = get_user_by_session(session_data.session_id, db)
        setattr(user, "avatar", out_path if avatar is not None else None)
        db.commit()
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
        data = SessionData(
            username=name, userid=user.id, session_id=session_data.session_id
        )
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
    try:
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
    link: str = Query(..., description="""YouTube link to the music video or phrase to search"""),
    queue_num: Optional[int] = Query(
        None,
        description="""Index of song in playlist after which this **Song** should be put in.""",
    ),
    session_data: SessionData = Depends(verifier),
    db: Session = Depends(get_db),
):
    """
    Adds a **Song** to the **Room** playlist or searches for this song in the YT.

    Returns a **Song** object if link given. If search phrase is given, returns list of links instead.

        Note that this method does not play a song. To play a song use /playnext, /playprev or /playthis instead.
    """
    try:
        user: models.User = get_user_by_session(session_data.session_id, db)
        a = db.query(models.Association).filter(models.Association.user == user).one()
        room = db.query(models.Room).filter(models.Room.id == a.room_id).one()

        yt = YouTube(link)
        avatar = f'https://img.youtube.com/vi/{yt.video_id}/hqdefault.jpg'

        playlist: list[models.Song] = get_room_playlist(room, db)
        if queue_num is None:
            if len(playlist) == 0:
                song = models.Song(
                    user=user,
                    link=yt.streams.filter(only_audio=True)[0].url,
                    avatar=avatar,
                    room=room,
                    queue_num=1,
                    status=models.SongState.in_queue,
                )
                db.add(song)
                db.commit()
                return song
            queue_num = max([i.queue_num for i in playlist])
        if all(i.queue_num != queue_num for i in playlist):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No song found with queue index {queue_num}",
            )

        for i in range(len(playlist)):
            if playlist[i].queue_num == queue_num:
                song = models.Song(
                    user=user,
                    link=yt.streams.filter(only_audio=True)[0].url,
                    room=room,
                    avatar=avatar,
                    queue_num=queue_num + 1,
                    status=models.SongState.in_queue,
                )
                db.add(song)
            if playlist[i].queue_num > queue_num:
                setattr(playlist[i], "queue_num", playlist[i].queue_num + 1)
        db.commit()
    except pytube.exceptions.RegexMatchError:
        res: list[pytube.YouTube] = pytube.Search(link).results.copy()
        if res:
            if len(res) > 5:
                res = res[:5]
            res = [{'link':'https://www.youtube.com/watch?v=' + i.video_id, 'title':i.title, 'img':f'https://img.youtube.com/vi/{i.video_id}/hqdefault.jpg'} for i in res]

        return Response(status_code=449, content=json.dumps(res), media_type='application/json')  # Retry with
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
        playlist: list[models.Song] = get_room_playlist(room, db)
        if not playlist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Playlist is empty."
            )
        if len(playlist) == 1:
            setattr(playlist[0], "status", models.SongState.is_playing)
            db.commit()
            return playlist[0]
        current_index = max(
            [
                i.queue_num if i.status == models.SongState.is_playing else 0
                for i in playlist
            ]
        )
        if not current_index:
            setattr(playlist[0], "status", models.SongState.is_playing)
            db.commit()
            return playlist[0]
        if current_index == playlist[-1].queue_num:
            setattr(playlist[0], "status", models.SongState.is_playing)
            for i in playlist[1:]:
                setattr(i, "status", models.SongState.in_queue)
            db.commit()
            return playlist[0]
        else:
            for i in playlist:
                if i.queue_num == current_index:
                    setattr(i, "status", models.SongState.played)
                elif i.queue_num == current_index + 1:
                    setattr(i, "status", models.SongState.is_playing)
                    song = i
            db.commit()
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
        playlist: list[models.Song] = get_room_playlist(room, db)
        if not playlist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Playlist is empty."
            )
        if len(playlist) == 1:
            setattr(playlist[0], "status", models.SongState.is_playing)
            db.commit()
            return playlist[0]
        current_index = max(
            [
                i.queue_num if i.status == models.SongState.is_playing else 0
                for i in playlist
            ]
        )
        if current_index == playlist[0].queue_num:
            setattr(playlist[-1], "status", models.SongState.is_playing)
            setattr(playlist[0], "status", models.SongState.in_queue)
            db.commit()
            return playlist[-1]
        else:
            for i in playlist:
                if i.queue_num == current_index:
                    setattr(i, "status", models.SongState.in_queue)
                elif i.queue_num == current_index - 1:
                    setattr(i, "status", models.SongState.is_playing)
                    song = i
            db.commit()
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


@router.patch(
    "/playthis",
    dependencies=[Depends(cookie)],
    response_model=schemas.Song,
    tags=["Songs"],
)
async def playthis(
    queue_num: int = Query(..., description="""Song index"""),
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
        playlist: list[models.Song] = get_room_playlist(room, db)
        if not playlist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Playlist is empty."
            )
        if all(i.queue_num != queue_num for i in playlist):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"There is no song in this room playlist with index {queue_num}.",
            )
        for i in playlist:
            if i.queue_num < queue_num:
                setattr(i, "status", models.SongState.played)
            elif i.queue_num > queue_num:
                setattr(i, "status", models.SongState.in_queue)
            else:
                setattr(i, "status", models.SongState.is_playing)
                song = i
        db.commit()
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


@router.patch(
    "/swap_songs",
    dependencies=[Depends(cookie)],
    response_model=schemas.Success,
    tags=["Songs"],
)
async def swap_songs(
    queue_num1: int = Query(..., description="""Song index"""),
    queue_num2: int = Query(..., description="""Song index"""),
    session_data: SessionData = Depends(verifier),
    db: Session = Depends(get_db),
):
    """
    Swaps **Songs** with given indexes in the room playlist.
    """
    try:
        user: models.User = get_user_by_session(session_data.session_id, db)
        a = db.query(models.Association).filter(models.Association.user == user).one()
        room = db.query(models.Room).filter(models.Room.id == a.room_id).one()
        playlist: list[models.Song] = get_room_playlist(room, db)
        l, h = (
            min(queue_num1, queue_num2),
            max(queue_num1, queue_num2),
        )  # lower, higher in playlist
        current_index = max(
            [
                i.queue_num if i.status == models.SongState.is_playing else 0
                for i in playlist
            ]
        )
        if all(i.queue_num != l for i in playlist) or all(
            i.queue_num != h for i in playlist
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"There is no song in this room playlist with index {l} or with index {h}.",
            )
        if l == h:
            return schemas.Success()
        if not current_index or current_index < l or current_index > h:
            for i in playlist:
                if i.queue_num == l:
                    setattr(i, "queue_num", h)
                elif i.queue_num == h:
                    setattr(i, "queue_num", l)
            db.commit()
            return schemas.Success()
        if current_index == l:
            for i in range(l + 1, h):
                setattr(playlist[i], "status", models.SongState.played)
            setattr(playlist[h], "status", models.SongState.played)
        elif current_index == h:
            for i in range(l + 1, h):
                setattr(playlist[i], "status", models.SongState.in_queue)
            setattr(playlist[l], "status", models.SongState.in_queue)
        else:
            setattr(playlist[h], "status", models.SongState.played)
            setattr(playlist[l], "status", models.SongState.in_queue)
        setattr(playlist[h], "queue_num", l)
        setattr(playlist[l], "queue_num", h)
        db.commit()
        return schemas.Success()

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
    queue_num: int = Query(..., description="""Song index"""),
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
        playlist: list[models.Song] = get_room_playlist(room, db)
        if all(i.queue_num != queue_num for i in playlist):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"There is no song in this room playlist with index {queue_num}.",
            )
        for i in range(len(playlist)):
            if i + 1 == queue_num:
                song = playlist[i]
                continue
            if i + 1 > queue_num:
                setattr(playlist[i], "queue_num", playlist[i].queue_num - 1)
        db.delete(song)
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
        playlist = get_room_playlist(room, db)

        for i in playlist:
            if i.status == models.SongState.is_playing:
                return i
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


@router.get(
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
        return schemas.Playlist(songs=get_room_playlist(room, db))
    except NoResultFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This user has no association with any room.",
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


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


@router.get("/get_img", response_class=FileResponse)
async def get_img(path: str = Query(..., description="""Image file path""")):
    """
    Returns image **File** if such exists.
    """
    try:
        f = open(path, "rb")
        f.close()
        if path.split("/")[0] != "images":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Image is not found."
            )
        return FileResponse(path=path)
    except OSError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Image is not found."
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/lets_drink_tea", response_class=HTMLResponse)
async def drink_tea(response: HTMLResponse):
    """
    *You seem tired, aren't you? Let's have a cup of tea and relax...*
    """
    response.status_code = status.HTTP_418_IM_A_TEAPOT
    return response.render("".join(open("tea.html", "r")))
