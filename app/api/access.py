"""Единая политика внешних действий, включая служебные HTTP-маршруты."""

from pathlib import Path
import tomllib

from core.utils.security import decode_token
from app.core.blocklist import is_blocked
from fastapi import Request
from fastapi.routing import iter_route_contexts
from fastapi.responses import JSONResponse
from fastbase.errors.codes import merge_mappings, resolve_code
from starlette.routing import Match

from app.core.exceptions import ForbiddenError, UnauthorizedError

POLICY_FILE = Path(__file__).resolve().parents[2] / "config" / "access.toml"


def load_policy(path: Path = POLICY_FILE) -> dict[str, frozenset[str]]:
    with path.open("rb") as stream:
        config = tomllib.load(stream)
    roles = config.get("roles")
    if set(config) != {"roles"} or not isinstance(roles, dict) or "guest" not in roles:
        raise ValueError("Access policy must declare roles, including guest")
    policy = {}
    for role, rule in roles.items():
        if not isinstance(role, str) or not role or not isinstance(rule, dict):
            raise ValueError("Invalid access role")
        actions = rule.get("scenarios")
        if set(rule) != {"scenarios"} or not isinstance(actions, list):
            raise ValueError(f"Invalid scenarios for role {role}")
        if any(not isinstance(a, str) or not a or "*" in a for a in actions):
            raise ValueError(f"Invalid scenario for role {role}")
        if len(actions) != len(set(actions)):
            raise ValueError(f"Duplicate scenario for role {role}")
        policy[role] = frozenset(actions)
    return policy


def external_scenario(action: str, *, core: str | None = None):
    """Связывает HTTP-обработчик с действием политики и внутренним сценарием."""
    def decorate(endpoint):
        endpoint.external_action = action
        endpoint.core_scenario = core
        return endpoint
    return decorate


def authenticate(authorization: str | None, policy: dict) -> dict:
    if authorization is None:
        return {"user_id": None, "role": "guest"}
    scheme, separator, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not separator or not token or token.strip() != token:
        raise UnauthorizedError("Invalid authorization header")
    try:
        payload = decode_token(token)
        role, subject = payload.get("role"), payload.get("sub")
        if (payload.get("type") != "access" or not isinstance(role, str)
                or role == "guest" or role not in policy
                or not isinstance(subject, (str, int)) or isinstance(subject, bool)
                or not str(subject).isascii() or not str(subject).isdigit() or int(subject) <= 0):
            raise ValueError("Invalid principal")
        user_id = int(subject)
    except Exception:
        raise UnauthorizedError("Invalid or expired token") from None
    # Блокировка действует сразу, не дожидаясь истечения токена доступа.
    if is_blocked(user_id):
        raise UnauthorizedError("Account is blocked")
    return {"user_id": user_id, "role": role}


def authorize(principal: dict, action: str | None, policy: dict) -> None:
    role = principal.get("role")
    if not isinstance(role, str) or action not in policy.get(role, ()):
        if role == "guest":
            raise UnauthorizedError("Authentication required")
        raise ForbiddenError("Access denied")


def route_action(route):
    return getattr(getattr(route, "endpoint", None), "external_action", None)


class AccessMiddleware:
    """Проверка до запуска обработчика; маршрут без политики закрыт."""

    def __init__(self, app, *, application, policy, settings):
        self.app, self.application, self.policy = app, application, policy
        self.mapping = merge_mappings(settings.error_codes)
        self.fallback = settings.error_code_fallback

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            route = next((r for r in iter_route_contexts(self.application.routes)
                          if r.matches(scope)[0] == Match.FULL), None)
            if route is not None:
                request = Request(scope)
                try:
                    principal = authenticate(request.headers.get("authorization"), self.policy)
                    authorize(principal, route_action(route), self.policy)
                    scope.setdefault("state", {})["principal"] = principal
                except (UnauthorizedError, ForbiddenError) as exc:
                    response = JSONResponse(
                        status_code=exc.http_status,
                        content={"success": False, "error": {
                            "code": resolve_code(exc, self.mapping, self.fallback),
                            "message": str(exc), "details": None,
                        }},
                    )
                    await response(scope, receive, send)
                    return
        await self.app(scope, receive, send)


def install_access(app, settings, policy=None):
    policy = load_policy() if policy is None else policy
    technical = {settings.docs_url: "service.docs", settings.openapi_url: "service.openapi",
                 settings.redoc_url: "service.redoc"}
    if settings.docs_url:
        technical[settings.docs_url.rstrip("/") + "/oauth2-redirect"] = "service.docs"
    for route in iter_route_contexts(app.routes):
        if route.path in technical:
            route.endpoint.external_action = technical[route.path]
    app.state.access_policy = policy
    app.add_middleware(AccessMiddleware, application=app, policy=policy, settings=settings)
    # Keep fastbase request-id and access logging outside authorization responses.
    app.user_middleware.append(app.user_middleware.pop(0))
