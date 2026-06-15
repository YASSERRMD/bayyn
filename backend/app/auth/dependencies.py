"""FastAPI dependencies for authentication."""
from __future__ import annotations
import uuid
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.jwt_handler import decode_access_token

_bearer = HTTPBearer(auto_error=False)


class CurrentUser:
    def __init__(self, user_id: uuid.UUID, email: str):
        self.id = user_id
        self.email = email


def _parse_token(
    credentials: Optional[HTTPAuthorizationCredentials],
) -> Optional[CurrentUser]:
    if credentials is None:
        return None
    payload = decode_access_token(credentials.credentials)
    if payload is None:
        return None
    try:
        return CurrentUser(user_id=uuid.UUID(payload["sub"]), email=payload["email"])
    except (KeyError, ValueError):
        return None


async def get_optional_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(_bearer)],
) -> Optional[CurrentUser]:
    """Return the authenticated user or None (anonymous allowed)."""
    return _parse_token(credentials)


async def get_required_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(_bearer)],
) -> CurrentUser:
    """Return the authenticated user or raise 401."""
    user = _parse_token(credentials)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


OptionalUser = Annotated[Optional[CurrentUser], Depends(get_optional_user)]
RequiredUser = Annotated[CurrentUser, Depends(get_required_user)]
