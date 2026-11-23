from fastapi import Request

from app.api.access import authenticate
from app.core.exceptions import UnauthorizedError


async def get_current_user(request: Request) -> dict:
    principal = getattr(request.state, "principal", None)
    if principal is None:
        principal = authenticate(request.headers.get("authorization"), request.app.state.access_policy)
    if principal["role"] == "guest":
        raise UnauthorizedError("Authentication required")
    return principal
