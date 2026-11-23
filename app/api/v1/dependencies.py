from functools import wraps
from typing import Optional, List, Callable

from fastapi import Header
from core.utils.security import decode_token
from app.core.exceptions import UnauthorizedError, ForbiddenError


async def get_current_user(authorization: str = Header(...)) -> dict:
    if not authorization.startswith("Bearer "):
        raise UnauthorizedError("Invalid authorization header")
    token = authorization[7:]
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise UnauthorizedError("Invalid token type")
        return {"user_id": int(payload["sub"]), "role": payload["role"]}
    except UnauthorizedError:
        raise
    except Exception:
        raise UnauthorizedError("Invalid or expired token")


def require_auth(allowed_roles: Optional[List[str]] = None):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get("current_user")
            if current_user is None:
                for arg in args:
                    if isinstance(arg, dict) and "user_id" in arg and "role" in arg:
                        current_user = arg
                        break
            if current_user is None:
                raise UnauthorizedError("Authentication required")
            if allowed_roles is not None:
                user_role = current_user.get("role")
                if user_role not in allowed_roles:
                    raise ForbiddenError(
                        f"Access denied. Required: {allowed_roles}, got: {user_role}"
                    )
            return await func(*args, **kwargs)
        return wrapper
    return decorator
