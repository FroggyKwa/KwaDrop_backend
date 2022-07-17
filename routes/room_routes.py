from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.params import Query
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session

from FastApi_sessions.fastapi_session import SessionData, cookie, verifier
from database.db import get_db
from db_methods.db_methods import (
    get_user_by_session,
    create_room as db_create_room,
)
from models import models, schemas


router = APIRouter()


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
        # if a.usertype not in (models.UserType.host, models.UserType.moder):  todo: Илья исправить должен чет на фронте
        #     raise HTTPException(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         detail="This user has no permission to edit this room.",
        #     )
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


@router.post(
    "/connect",
    dependencies=[Depends(cookie)],
    tags=["Room"],
    response_model=schemas.Room,
)
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
