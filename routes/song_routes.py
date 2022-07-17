import json
from typing import Optional

import pytube.exceptions
from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.params import Query
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session

from FastApi_sessions.fastapi_session import SessionData, cookie, verifier
from database.db import get_db
from db_methods.db_methods import (
    get_user_by_session,
    get_room_playlist,
)
from models import models, schemas
from pytube import YouTube

router = APIRouter()



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
                    title=yt.title,
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
                    title=yt.title,
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
                setattr(playlist[i - 1], "status", models.SongState.played)
            setattr(playlist[h - 1], "status", models.SongState.played)
        elif current_index == h:
            for i in range(l + 1, h):
                setattr(playlist[i - 1], "status", models.SongState.in_queue)
            setattr(playlist[l - 1], "status", models.SongState.in_queue)
        else:
            setattr(playlist[h - 1], "status", models.SongState.played)
            setattr(playlist[l - 1], "status", models.SongState.in_queue)
        setattr(playlist[h - 1], "queue_num", l)
        setattr(playlist[l - 1], "queue_num", h)
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
