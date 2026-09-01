import base64
import html
import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse, Response

from app.config import basic_auth_credentials

_REALM = 'Basic realm="DSP Data Tool"'
_PUBLIC_PATHS = frozenset({"/health"})
_LOCAL_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})

_LOGIN_PAGE = """<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Вход — DSP Data Tool</title>
  <style>
    body { font-family: system-ui, sans-serif; margin: 0; background: #f4f5f7; color: #1a1a1a; }
    main { max-width: 360px; margin: 12vh auto; background: #fff; padding: 28px 24px;
           border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,.08); }
    h1 { font-size: 1.2rem; margin: 0 0 8px; }
    p { color: #555; font-size: .9rem; margin: 0 0 16px; }
    label { display: block; font-size: .8rem; margin: 10px 0 4px; }
    input { width: 100%; box-sizing: border-box; padding: 8px 10px; border: 1px solid #ccc;
            border-radius: 8px; }
    button { margin-top: 16px; width: 100%; padding: 10px; border: 0; border-radius: 8px;
             background: #1f4b99; color: #fff; font-size: 1rem; cursor: pointer; }
    #err { color: #b00020; margin-top: 12px; }
  </style>
</head>
<body>
  <main>
    <h1>DSP Data Tool</h1>
    <p>Нужны логин и пароль из .env</p>
    <form id="f">
      <label for="user">Логин</label>
      <input id="user" name="user" autocomplete="username" value="__USER__" required>
      <label for="password">Пароль</label>
      <input id="password" name="password" type="password" autocomplete="current-password" required>
      <button type="submit">Войти</button>
      <p id="err" hidden>Неверный логин или пароль</p>
    </form>
  </main>
  <script>
    document.getElementById('f').addEventListener('submit', function (e) {
      e.preventDefault();
      var u = document.getElementById('user').value;
      var p = document.getElementById('password').value;
      var xhr = new XMLHttpRequest();
      xhr.open('GET', '/api/partners', true, u, p);
      xhr.onload = function () {
        if (xhr.status === 200) location.replace('/');
        else document.getElementById('err').hidden = false;
      };
      xhr.onerror = function () { document.getElementById('err').hidden = false; };
      xhr.send();
    });
  </script>
</body>
</html>
"""


def _request_host(request: Request) -> str:
    host = (request.headers.get("host") or "").strip()
    if host.startswith("["):
        end = host.find("]")
        return host[1:end].lower() if end != -1 else host.lower()
    return host.split(":")[0].lower()


def _is_local_request(request: Request) -> bool:
    return _request_host(request) in _LOCAL_HOSTS


def _unauthorized(request: Request, username: str = "") -> Response:
    headers = {"WWW-Authenticate": _REALM}
    accept = (request.headers.get("accept") or "").lower()
    if "text/html" in accept:
        body = _LOGIN_PAGE.replace("__USER__", html.escape(username, quote=True))
        return HTMLResponse(status_code=401, content=body, headers=headers)
    return Response(
        status_code=401,
        content="Требуется авторизация",
        media_type="text/plain; charset=utf-8",
        headers=headers,
    )


class BasicAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        user, password = basic_auth_credentials()
        if not user:
            return await call_next(request)
        if request.url.path in _PUBLIC_PATHS:
            return await call_next(request)
        if _is_local_request(request):
            return await call_next(request)

        header = request.headers.get("Authorization") or ""
        scheme, _, param = header.partition(" ")
        if scheme.lower() != "basic" or not param.strip():
            return _unauthorized(request, user)
        try:
            decoded = base64.b64decode(param.strip()).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            return _unauthorized(request, user)
        given_user, _, given_password = decoded.partition(":")
        user_ok = secrets.compare_digest(given_user.encode("utf-8"), user.encode("utf-8"))
        pass_ok = secrets.compare_digest(
            given_password.encode("utf-8"), password.encode("utf-8")
        )
        if not (user_ok and pass_ok):
            return _unauthorized(request, user)
        return await call_next(request)
