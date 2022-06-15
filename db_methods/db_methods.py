from models import models

from database.db import get_db

from sqlalchemy.orm import Session

from fastapi import HTTPException, Depends, status


def create_user(name: str, session_id: str, db: Session):
    try:
        user = models.User(name=name, session_id=session_id)
        db.add(user)
        # db.commit()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return user
