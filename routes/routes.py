from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.exc import IntegrityError
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


@router.post("/create_room", dependencies=[Depends(cookie)])
async def create_room(
    name: str, password: Optional[str], session_data: SessionData = Depends(verifier), db: Session = Depends(get_db)
):
    try:
        print(session_data.session_id, type(session_data.session_id))
        user = get_user_by_session(session_data.session_id, db)
        print('hui')
        room = db_create_room(name, password, user, db)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return room


@router.post("/create_session", dependencies=[Depends(cookie)])
async def create_session(response: Response, session_data: SessionData = Depends(verifier.my_call)):
    try:
        if session_data is not None:
            print(session_data)
            return f"session already exists"
        session = uuid4()
        data = SessionData(session_id=str(session))

        await backend.create(session, data)
        cookie.attach_to_response(response, session)

        return f"created session"
    except Exception as e:
        print(e, str(e), e.__repr__(), sep='\n')
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/whoami", dependencies=[Depends(cookie)])
async def whoami(session_data: SessionData = Depends(verifier)):
    print(session_data)
    print(backend.data)
    print(cookie.cookie_params.dict())
    return session_data


@router.delete("/delete_session")
async def del_session(response: Response, session_id: UUID = Depends(cookie)):
    await backend.delete(session_id)
    cookie.delete_from_response(response)
    return "deleted session"
