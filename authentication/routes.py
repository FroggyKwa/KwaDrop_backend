import uuid

from fastapi import APIRouter, Depends
from starlette.responses import Response

from helpers import generate_random_name
from authentication.schemas import SessionData
from authentication.sessions import backend, cookie
from authentication.verifier import verifier

router = APIRouter(prefix="/sessions")


@router.post("/create_session", tags=["sessions"])
async def create_session(response: Response, name: str = generate_random_name(), room_id: int = None):
    session_id = uuid.uuid4()
    data = SessionData(name=name, connected_room_id=room_id)
    await backend.create(session_id, data)
    cookie.attach_to_response(response, session_id)
    return cookie.cookie_params


@router.get("/whoami", dependencies=[Depends(cookie)], tags=["sessions"])
async def whoami(session_data: SessionData = Depends(verifier)):
    return session_data


@router.post("/delete_session", tags=["sessions"])
async def delete_session(response: Response, session_id: uuid.UUID = Depends(cookie)):
    await backend.delete(session_id)
    cookie.delete_from_response(response)
    return cookie.cookie_params
