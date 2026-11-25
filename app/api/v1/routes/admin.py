from core import run
from fastapi import APIRouter, Depends, Header, Query, Request
from app.api.access import external_scenario
from app.api.v1.dependencies import get_current_user
from app.scenarios.admin.admins import AdminListAdminsDTO, AdminListAdminsResponse
from app.scenarios.admin.profile import AdminGetMyProfileDTO, AdminGetMyProfileResponse
from app.scenarios.admin.students import AdminListStudentsDTO, AdminListStudentsResponse
from app.scenarios.admin.tutors import AdminListTutorsDTO, AdminListTutorsResponse
from app.scenarios.admin.users import (
    AdminGetUserByIdDTO,
    AdminGetUserByIdResponse,
    AdminListUsersDTO,
    AdminListUsersResponse,
    AdminUpdateUserDTO,
    AdminUpdateUserResponse,
)

from app.scenarios.admin.panel import (
    AdminActorDTO, AdminKeyResponse, AuditListDTO, AuditListResponse, DashboardResponse,
    UserActionDTO, UserActionResponse,
)
from app.scenarios.admin.database import (
    DbActorDTO, RowChangeDTO, RowChangeResponse, RowsDTO, RowsResponse, SqlDTO, SqlResponse, TablesResponse,
)
from pydantic import BaseModel, Field

router = APIRouter(prefix="/admin", tags=["admin"])


def client_ip(request: Request) -> str | None:
    """Адрес владельца для журнала (за nginx — реальный, при FORWARDED_ALLOW_IPS)."""
    return request.client.host if request.client else None


@router.get("/me", response_model=AdminGetMyProfileResponse)
@external_scenario("admin.get_my_profile", core="admin_get_my_profile")
async def get_my_profile(
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto = AdminGetMyProfileDTO(access_token=authorization.split(" ")[1])
    return await run("admin_get_my_profile", dto)


@router.get("/users", response_model=AdminListUsersResponse)
@external_scenario("admin.list_users", core="admin_list_users")
async def list_users(
    role: str | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto = AdminListUsersDTO(
        access_token=authorization.split(" ")[1],
        role=role,
        limit=limit,
        offset=offset,
    )
    return await run("admin_list_users", dto)


@router.get("/users/{user_id}", response_model=AdminGetUserByIdResponse)
@external_scenario("admin.get_user_by_id", core="admin_get_user_by_id")
async def get_user_by_id(
    user_id: int,
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto = AdminGetUserByIdDTO(
        access_token=authorization.split(" ")[1],
        target_user_id=user_id,
    )
    return await run("admin_get_user_by_id", dto)


@router.patch("/users/{user_id}", response_model=AdminUpdateUserResponse)
@external_scenario("admin.update_user", core="admin_update_user")
async def update_user(
    user_id: int,
    dto: AdminUpdateUserDTO,
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto.access_token = authorization.split(" ")[1]
    dto.target_user_id = user_id
    return await run("admin_update_user", dto)


@router.get("/students", response_model=AdminListStudentsResponse)
@external_scenario("admin.list_students", core="admin_list_students")
async def list_students(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto = AdminListStudentsDTO(
        access_token=authorization.split(" ")[1],
        limit=limit,
        offset=offset,
    )
    return await run("admin_list_students", dto)


@router.get("/tutors", response_model=AdminListTutorsResponse)
@external_scenario("admin.list_tutors", core="admin_list_tutors")
async def list_tutors(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto = AdminListTutorsDTO(
        access_token=authorization.split(" ")[1],
        limit=limit,
        offset=offset,
    )
    return await run("admin_list_tutors", dto)


@router.get("/admins", response_model=AdminListAdminsResponse)
@external_scenario("admin.list_admins", core="admin_list_admins")
async def list_admins(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    authorization: str = Header(...),
    current_user: dict = Depends(get_current_user),
):
    dto = AdminListAdminsDTO(
        access_token=authorization.split(" ")[1],
        limit=limit,
        offset=offset,
    )
    return await run("admin_list_admins", dto)


# ===== Админ-панель владельца =====

@router.get("/dashboard", response_model=DashboardResponse)
@external_scenario("admin.dashboard", core="admin_dashboard")
async def dashboard(request: Request, user: dict = Depends(get_current_user)):
    return await run("admin_dashboard", AdminActorDTO(actor_id=user["user_id"], ip=client_ip(request)))


@router.post("/key/rotate", response_model=AdminKeyResponse)
@external_scenario("admin.rotate_key", core="admin_rotate_key")
async def rotate_key(request: Request, user: dict = Depends(get_current_user)):
    return await run("admin_rotate_key", AdminActorDTO(actor_id=user["user_id"], ip=client_ip(request)))


@router.get("/audit", response_model=AuditListResponse)
@external_scenario("admin.audit", core="admin_audit_list")
async def audit_list(request: Request, action: str | None = Query(default=None, max_length=64),
                     limit: int = Query(default=100, ge=1, le=500), offset: int = Query(default=0, ge=0),
                     user: dict = Depends(get_current_user)):
    return await run("admin_audit_list", AuditListDTO(
        actor_id=user["user_id"], ip=client_ip(request), action=action, limit=limit, offset=offset))


class ReasonBody(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


async def _user_action(core: str, request: Request, user: dict, user_id: int, reason: str | None = None):
    return await run(core, UserActionDTO(actor_id=user["user_id"], ip=client_ip(request), user_id=user_id, reason=reason))


@router.post("/users/{user_id}/block", response_model=UserActionResponse)
@external_scenario("admin.block_user", core="admin_block_user")
async def block_user(request: Request, body: ReasonBody, user_id: int, user: dict = Depends(get_current_user)):
    return await _user_action("admin_block_user", request, user, user_id, body.reason)


@router.post("/users/{user_id}/unblock", response_model=UserActionResponse)
@external_scenario("admin.unblock_user", core="admin_unblock_user")
async def unblock_user(request: Request, user_id: int, user: dict = Depends(get_current_user)):
    return await _user_action("admin_unblock_user", request, user, user_id)


@router.post("/users/{user_id}/reset-password", response_model=UserActionResponse)
@external_scenario("admin.reset_password", core="admin_reset_password")
async def reset_password(request: Request, user_id: int, user: dict = Depends(get_current_user)):
    return await _user_action("admin_reset_password", request, user, user_id)


@router.delete("/users/{user_id}", response_model=UserActionResponse)
@external_scenario("admin.delete_user", core="admin_delete_user")
async def delete_user(request: Request, user_id: int, user: dict = Depends(get_current_user)):
    return await _user_action("admin_delete_user", request, user, user_id)


# --- База данных ---

@router.get("/db/tables", response_model=TablesResponse)
@external_scenario("admin.db_tables", core="admin_db_tables")
async def db_tables(request: Request, user: dict = Depends(get_current_user)):
    return await run("admin_db_tables", DbActorDTO(actor_id=user["user_id"], ip=client_ip(request)))


@router.get("/db/tables/{table}", response_model=RowsResponse)
@external_scenario("admin.db_rows", core="admin_db_rows")
async def db_rows(request: Request, table: str, search: str | None = Query(default=None, max_length=200),
                  order_by: str | None = Query(default=None, max_length=63), desc: bool = True,
                  limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0),
                  user: dict = Depends(get_current_user)):
    return await run("admin_db_rows", RowsDTO(
        actor_id=user["user_id"], ip=client_ip(request), table=table, search=search,
        order_by=order_by, desc=desc, limit=limit, offset=offset))


class RowBody(BaseModel):
    pk: dict
    values: dict = {}


@router.patch("/db/tables/{table}/row", response_model=RowChangeResponse)
@external_scenario("admin.db_update_row", core="admin_db_update_row")
async def db_update_row(request: Request, table: str, body: RowBody, user: dict = Depends(get_current_user)):
    return await run("admin_db_update_row", RowChangeDTO(
        actor_id=user["user_id"], ip=client_ip(request), table=table, pk=body.pk, values=body.values))


@router.post("/db/tables/{table}/row/delete", response_model=RowChangeResponse)
@external_scenario("admin.db_delete_row", core="admin_db_delete_row")
async def db_delete_row(request: Request, table: str, body: RowBody, user: dict = Depends(get_current_user)):
    return await run("admin_db_delete_row", RowChangeDTO(
        actor_id=user["user_id"], ip=client_ip(request), table=table, pk=body.pk))


class SqlBody(BaseModel):
    sql: str = Field(min_length=1, max_length=20000)
    write: bool = False
    confirm: bool = False


@router.post("/db/sql", response_model=SqlResponse)
@external_scenario("admin.db_sql", core="admin_db_sql")
async def db_sql(request: Request, body: SqlBody, user: dict = Depends(get_current_user)):
    return await run("admin_db_sql", SqlDTO(
        actor_id=user["user_id"], ip=client_ip(request), sql=body.sql, write=body.write, confirm=body.confirm))
