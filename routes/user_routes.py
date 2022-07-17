import secrets
from typing import Optional

from helpers import save_file
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile
from fastapi.params import Query, File
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.orm import Session

from FastApi_sessions.fastapi_session import SessionData, backend, cookie, verifier
from database.db import get_db
from db_methods.db_methods import (
    create_user as db_create_user,
    get_user_by_session,
)
from models import models, schemas
from uuid import UUID

router = APIRouter()


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
