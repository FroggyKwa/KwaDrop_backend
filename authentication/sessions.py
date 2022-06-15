from uuid import UUID

import secrets
from fastapi import HTTPException
from fastapi_sessions.backends import SessionBackend
from fastapi_sessions.backends.session_backend import SessionModel
from fastapi_sessions.frontends.implementations import SessionCookie, CookieParameters
from fastapi_sessions.backends.implementations import InMemoryBackend
from fastapi_sessions.frontends.session_frontend import ID
from fastapi_sessions.session_verifier import SessionVerifier

from authentication.schemas import SessionData

cookie_params = CookieParameters()

cookie = SessionCookie(
    cookie_name="_session",
    identifier="session_verifier",
    auto_error=True,
    secret_key=secrets.token_hex(),
    cookie_params=cookie_params,
)

backend = InMemoryBackend[UUID, SessionData]()


class BasicVerifier(SessionVerifier[UUID, SessionData]):
    def __init__(
        self,
        *,
        identifier: str,
        auto_error: bool,
        backend: InMemoryBackend[UUID, SessionData],
        auth_http_exception: HTTPException,
    ):
        self._identifier = identifier
        self._auto_error = auto_error
        self._backend = backend
        self._auth_http_exception = auth_http_exception

    @property
    def identifier(self) -> str:
        return self._identifier

    @property
    def backend(self) -> SessionBackend[ID, SessionModel]:
        return self._backend

    @property
    def auto_error(self) -> bool:
        return self._auto_error

    @property
    def auth_http_exception(self) -> HTTPException:
        return self._auth_http_exception

    def verify_session(self, model: SessionModel) -> bool:
        return True
