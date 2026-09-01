import base64
import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.config import basic_auth_credentials

_REALM = 'Basic realm="DSP Data Tool"'
_PUBLIC_PATHS = frozenset({"/health"})


def _unauthorized() -> Response:
    return Response(
        status_code=401,
        content="Требуется авторизация",
        media_type="text/plain; charset=utf-8",
        headers={"WWW-Authenticate": _REALM},
    )


class BasicAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        user, password = basic_auth_credentials()
        if not user:
            return await call_next(request)
        if request.url.path in _PUBLIC_PATHS:
            return await call_next(request)

        header = request.headers.get("Authorization") or ""
        scheme, _, param = header.partition(" ")
        if scheme.lower() != "basic" or not param.strip():
            return _unauthorized()
        try:
            decoded = base64.b64decode(param.strip()).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            return _unauthorized()
        given_user, _, given_password = decoded.partition(":")
        user_ok = secrets.compare_digest(given_user.encode("utf-8"), user.encode("utf-8"))
        pass_ok = secrets.compare_digest(
            given_password.encode("utf-8"), password.encode("utf-8")
        )
        if not (user_ok and pass_ok):
            return _unauthorized()
        return await call_next(request)
