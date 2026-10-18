from fastapi import Cookie, HTTPException, status
from itsdangerous import BadSignature, URLSafeSerializer

from .config import settings

_COOKIE_NAME = "staff_session"
_serializer = URLSafeSerializer(settings.secret_key, salt="staff")


def check_password(password: str) -> bool:
    return password == settings.staff_password


def make_session_token() -> str:
    return _serializer.dumps({"role": "staff"})


def _valid_token(token: str | None) -> bool:
    if not token:
        return False
    try:
        data = _serializer.loads(token)
        return data.get("role") == "staff"
    except BadSignature:
        return False


def is_staff(token: str | None) -> bool:
    return _valid_token(token)


def require_staff(staff_session: str | None = Cookie(default=None)) -> None:
    if not is_staff(staff_session):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Accesso riservato allo staff",
        )


COOKIE_NAME = _COOKIE_NAME
