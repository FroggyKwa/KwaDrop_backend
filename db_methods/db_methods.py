from models import models

from database.db import get_db

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from fastapi import HTTPException, Depends, status


def create_user(name: str, session_id: str, db: Session):
    try:
        user = models.User(name=name, session_id=session_id)
        db.add(user)
        # db.commit()
    except IntegrityError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User for this session already exists.")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return user


def get_user_by_session(session_id: str, db: Session):
    user: list[models.User] = db.query(models.User).get(session_id)
    try:
        assert user, "There is no user for this session"
    except AssertionError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return user