from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.orm import Session

from FastApi_sessions.fastapi_session import SessionData, backend, cookie, verifier
from database.db import get_db
from db_methods.db_methods import create_user as db_create_user, get_user_by_session, create_room as db_create_room
from models import models, schemas
from uuid import UUID, uuid4

router = APIRouter()


@router.post("/create_user", dependencies=[Depends(cookie)], response_model=schemas.User)
async def create_user(name: str, session_data: SessionData = Depends(verifier), db: Session = Depends(get_db)):
    try:
        session_id = session_data.dict()["session_id"]
        session_data.username = name
        user = db_create_user(name, session_id, db)
        db.commit()
    except IntegrityError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User for this session already exists.")
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return user


@router.patch("/rename_user", dependencies=[Depends(cookie)], response_model=schemas.User)
async def rename_user(name: str, session_data: SessionData = Depends((verifier)), db: Session = Depends(get_db)):
    try:
        user = get_user_by_session(session_data.session_id, db)
        setattr(user, 'name', name)
        db.commit()
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return user


@router.delete("/delete_user", dependencies=[Depends(cookie)], response_model=schemas.User)
async def delete_user(session_data: SessionData = Depends((verifier)), db: Session = Depends(get_db)):
    try: #todo: если юзер хост - удалаять комнату
        user: models.User = get_user_by_session(session_data.session_id, db)
        try:
            a = db.query(models.Association).filter(models.Association.user==user).one()
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


@router.post("/create_room", dependencies=[Depends(cookie)], response_model=schemas.Room)
async def create_room(
    name: str, password: Optional[str] = None, session_data: SessionData = Depends(verifier), db: Session = Depends(get_db)
):
    try:
        user = get_user_by_session(session_data.session_id, db)
        try:
            a = db.query(models.Association).filter(models.Association.user == user).one()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already has association to existing room.")
        except NoResultFound:
            pass
        room = db_create_room(name, password, user, db)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return room


@router.patch("/edit_room", dependencies=[Depends(cookie)], response_model=schemas.Room)
async def edit_room(
        name: Optional[str] = None, password: Optional[str] = None, session_data: SessionData = Depends(verifier), db: Session = Depends(get_db)
):
    try:
        user: models.User = get_user_by_session(session_data.session_id, db)
        a: models.Association = db.query(models.Association).filter(models.Association.user == user).one()
        if a.usertype not in (models.UserType.host, models.UserType.moder):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='This user has no permission to edit this room.')
        room = db.query(models.Room).filter(models.Room.id == a.room_id).one()
        if name is not None:
            setattr(room, 'name', name)
        if password is not None:
            setattr(room, 'password', password)
        db.commit()
    except NoResultFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="This user has no association with any room.")
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return room


@router.delete("/delete_room", dependencies=[Depends(cookie)], response_model=schemas.Room)
async def delete_room(session_data: SessionData = Depends(verifier), db: Session = Depends(get_db)):
    try:
        user: models.User = get_user_by_session(session_data.session_id, db)
        a: models.Association = db.query(models.Association).filter(models.Association.user == user).one()
        if a.usertype not in (models.UserType.host, models.UserType.moder):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail='This user has no permission to edit this room.')
        room = db.query(models.Room).filter(models.Room.id == a.room_id).one()
        a_list = db.query(models.Association).filter(models.Association.room == room).all()
        for i in a_list:
            db.delete(i)
        db.flush()
        db.delete(room)
        db.commit()
    except NoResultFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="This user has no association with any room.")
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return room



@router.post("/create_session", dependencies=[Depends(cookie)])
async def create_session(response: Response, session_data: SessionData = Depends(verifier.my_call)):
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


@router.get("/whoami", dependencies=[Depends(cookie)])
async def whoami(session_data: SessionData = Depends(verifier)):
    return session_data


@router.delete("/delete_session")
async def del_session(response: Response, session_id: UUID = Depends(cookie)):
    await backend.delete(session_id)
    cookie.delete_from_response(response)
    return "deleted session"
