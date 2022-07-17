from fastapi import APIRouter, Depends, HTTPException, status, Response, UploadFile
from fastapi.params import Query, File
from fastapi.responses import HTMLResponse, FileResponse


from FastApi_sessions.fastapi_session import SessionData, backend, cookie, verifier

from uuid import UUID, uuid4

router = APIRouter()


@router.post("/create_session", dependencies=[Depends(cookie)], tags=["Session"])
async def create_session(
    response: Response, session_data: SessionData = Depends(verifier.my_call)
):
    """
    Initializes a **Session** if one isn't initialized.
    """
    try:
        if session_data is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=f"session already exists"
            )
        session = uuid4()
        data = SessionData(session_id=str(session))

        await backend.create(session, data)
        cookie.attach_to_response(response, session)

        return f"created session"
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/whoami", dependencies=[Depends(cookie)], tags=["Session"])
async def whoami(session_data: SessionData = Depends(verifier)):
    """
    Returns **Session data** if session exists.
    """
    return session_data


@router.delete("/delete_session", tags=["Session"])
async def del_session(response: Response, session_id: UUID = Depends(cookie)):
    """
    Deletes a **Session** if one exists.
    """
    await backend.delete(session_id)
    cookie.delete_from_response(response)
    return "deleted session"


@router.get("/get_img", response_class=FileResponse)
async def get_img(path: str = Query(..., description="""Image file path""")):
    """
    Returns image **File** if such exists.
    """
    try:
        f = open(path, "rb")
        f.close()
        if path.split("/")[0] != "images":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Image is not found."
            )
        return FileResponse(path=path)
    except OSError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Image is not found."
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/lets_drink_tea", response_class=HTMLResponse)
async def drink_tea(response: HTMLResponse):
    """
    *You seem tired, aren't you? Let's have a cup of tea and relax...*
    """
    response.status_code = status.HTTP_418_IM_A_TEAPOT
    return response.render("".join(open("tea.html", "r")))
