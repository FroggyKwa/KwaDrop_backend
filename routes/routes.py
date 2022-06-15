from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session

from authentication.schemas import SessionData
from authentication.sessions import cookie
from authentication.verifier import verifier
from database.db import get_db
from db_methods.db_methods import create_user as db_create_user
from models import schemas

router = APIRouter()


@router.post("/create_user", response_model=schemas.User)
async def create_user(name: str, session_id: str, db: Session = Depends(get_db)):
    try:
        user = db_create_user(name, session_id, db)
        db.commit()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return user


@router.post("/create_room", dependencies=[Depends(cookie)])
async def create_room(
    name: str,
    password: Optional[str],
    session_data: SessionData = Depends(verifier),
    db: Session = Depends(get_db),
):
    try:
        room = None
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return room
