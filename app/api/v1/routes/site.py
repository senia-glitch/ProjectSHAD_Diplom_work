"""Гостевая страница: публичное чтение блоков и управление ими из админ-панели."""
from core import run
from fastapi import APIRouter, Depends, Path, Request
from pydantic import BaseModel, Field

from app.api.access import external_scenario
from app.api.v1.dependencies import get_current_user
from app.scenarios.site.blocks import (ActorDTO, BlockInput, BlockList, BlockRefDTO, Done, OrderDTO, SaveBlockDTO,
                                      SiteBlock)

router = APIRouter(tags=['site'])


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.get('/site/blocks', response_model=BlockList)
@external_scenario('site.blocks', core='site.blocks')
async def public_blocks():
    return await run('site.blocks', None)


@router.get('/admin/site/blocks', response_model=BlockList)
@external_scenario('admin.site_blocks', core='admin_site_blocks')
async def admin_blocks(request: Request, user: dict = Depends(get_current_user)):
    return await run('admin_site_blocks', ActorDTO(actor_id=user['user_id'], ip=_ip(request)))


@router.post('/admin/site/blocks', response_model=SiteBlock, status_code=201)
@external_scenario('admin.site_block_save', core='admin_site_block_save')
async def create_block(request: Request, body: BlockInput, user: dict = Depends(get_current_user)):
    return await run('admin_site_block_save', SaveBlockDTO(**body.model_dump(), actor_id=user['user_id'], ip=_ip(request)))


@router.put('/admin/site/blocks/{block_id}', response_model=SiteBlock)
@external_scenario('admin.site_block_save', core='admin_site_block_save')
async def update_block(request: Request, body: BlockInput, block_id: int = Path(gt=0),
                       user: dict = Depends(get_current_user)):
    return await run('admin_site_block_save', SaveBlockDTO(**body.model_dump(), actor_id=user['user_id'],
                                                           ip=_ip(request), block_id=block_id))


@router.delete('/admin/site/blocks/{block_id}', response_model=Done)
@external_scenario('admin.site_block_delete', core='admin_site_block_delete')
async def delete_block(request: Request, block_id: int = Path(gt=0), user: dict = Depends(get_current_user)):
    return await run('admin_site_block_delete', BlockRefDTO(actor_id=user['user_id'], ip=_ip(request), block_id=block_id))


class OrderBody(BaseModel):
    ids: list[int] = Field(max_length=30)


@router.post('/admin/site/blocks/order', response_model=BlockList)
@external_scenario('admin.site_blocks_order', core='admin_site_blocks_order')
async def order_blocks(request: Request, body: OrderBody, user: dict = Depends(get_current_user)):
    return await run('admin_site_blocks_order', OrderDTO(actor_id=user['user_id'], ip=_ip(request), ids=body.ids))
