from fastapi import HTTPException
from starlette import status

from authentication.sessions import BasicVerifier, backend

verifier = BasicVerifier(
    identifier="session_verifier",
    auto_error=True,
    backend=backend,
    auth_http_exception=HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail="Invalid session"
    ),
)
