from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database.db import get_db
from db_methods.db_methods import create_user as db_create_user
from models import models, schemas

router = APIRouter()


@router.post("/create_user", response_model=schemas.User)
async def create_user(name: str, session_id: str, db: Session = Depends(get_db)):

    try:
        user = db_create_user(name, session_id, db)
        db.commit()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return user


@router.post("/create_room")
async def create_room(
    name: str, session_id: str, password: Optional[str], db: Session = Depends(get_db)
):

    try:
        room = None
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return room
