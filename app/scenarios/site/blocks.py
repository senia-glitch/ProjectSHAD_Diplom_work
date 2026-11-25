"""Гостевая страница сайта из блоков: владелец редактирует их в админ-панели.

Виды блоков задают вёрстку, тексты — в Markdown: заголовок, текст и пункты
(преимущества, шаги, вопросы). Гость видит только включённые блоки по порядку.
"""
import json
from datetime import datetime, timezone
from typing import Literal

from core import BaseScenario, NotFoundError, ValidationError, register_scenario
from pydantic import BaseModel, Field, field_validator

from app.utils.admin_audit import audit

BlockKind = Literal['hero', 'features', 'steps', 'faq', 'text', 'cta']
MAX_BLOCKS = 30


class BlockItem(BaseModel):
    title: str = Field(default='', max_length=200)
    body: str = Field(default='', max_length=5000)


class BlockInput(BaseModel):
    kind: BlockKind
    title: str = Field(default='', max_length=200)
    body: str = Field(default='', max_length=20000)
    items: list[BlockItem] = Field(default_factory=list, max_length=24)
    visible: bool = True

    @field_validator('title')
    @classmethod
    def _title(cls, value):
        return ' '.join(value.split())


class SiteBlock(BlockInput):
    id: int
    position: int
    updated_at: datetime | None = None


class BlockList(BaseModel):
    items: list[SiteBlock]


class ActorDTO(BaseModel):
    actor_id: int = Field(gt=0)
    ip: str | None = None


class SaveBlockDTO(BlockInput):
    actor_id: int = Field(gt=0)
    ip: str | None = None
    block_id: int | None = Field(default=None, gt=0)


class BlockRefDTO(ActorDTO):
    block_id: int = Field(gt=0)


class OrderDTO(ActorDTO):
    ids: list[int] = Field(max_length=MAX_BLOCKS)


class Done(BaseModel):
    ok: bool = True


def _block(row) -> SiteBlock:
    try:
        items = [BlockItem(**i) for i in json.loads(row.get('items') or '[]') if isinstance(i, dict)]
    except (TypeError, ValueError):
        items = []
    return SiteBlock(id=row['id'], position=row['position'], kind=row['kind'], title=row['title'] or '',
                     body=row['body'] or '', items=items, visible=bool(row['visible']),
                     updated_at=row.get('updated_at'))


async def _all(db, visible_only=False) -> list[SiteBlock]:
    where = 'WHERE visible ' if visible_only else ''
    rows = await db.query(f'SELECT * FROM site_blocks {where}ORDER BY position, id', {})
    return [_block(r) for r in rows]


@register_scenario('site.blocks', dto=None, response=BlockList)
class PublicBlocks(BaseScenario):
    """Гостевая страница: включённые блоки по порядку."""
    async def execute(self, dto):
        return BlockList(items=await _all(self._db, visible_only=True))


@register_scenario('admin_site_blocks', dto=ActorDTO, response=BlockList)
class AdminBlocks(BaseScenario):
    async def execute(self, dto):
        return BlockList(items=await _all(self._db))


@register_scenario('admin_site_block_save', dto=SaveBlockDTO, response=SiteBlock)
class SaveBlock(BaseScenario):
    """Новый блок встаёт в конец страницы; существующий меняется на месте."""
    async def execute(self, dto):
        data = {'kind': dto.kind, 'title': dto.title, 'body': dto.body, 'visible': dto.visible,
                'items': json.dumps([i.model_dump() for i in dto.items], ensure_ascii=False),
                'updated_at': datetime.now(timezone.utc)}
        if dto.block_id:
            if not await self._db.read('site_blocks', dto.block_id):
                raise NotFoundError('Блок не найден')
            await self._db.update('site_blocks', dto.block_id, data)
            block_id, action = dto.block_id, 'site_block_update'
        else:
            count = await self._db.query('SELECT count(*) AS n, coalesce(max(position), -1) AS last FROM site_blocks', {})
            if count[0]['n'] >= MAX_BLOCKS:
                raise ValidationError(f'На странице не больше {MAX_BLOCKS} блоков')
            row = await self._db.create('site_blocks', {**data, 'position': count[0]['last'] + 1})
            block_id, action = row['id'], 'site_block_create'
        await audit(self._db, dto.actor_id, action, f'site_block:{block_id}', {'kind': dto.kind}, dto.ip)
        return _block(await self._db.read('site_blocks', block_id))


@register_scenario('admin_site_block_delete', dto=BlockRefDTO, response=Done)
class DeleteBlock(BaseScenario):
    async def execute(self, dto):
        if not await self._db.read('site_blocks', dto.block_id):
            raise NotFoundError('Блок не найден')
        await self._db.delete('site_blocks', dto.block_id)
        await audit(self._db, dto.actor_id, 'site_block_delete', f'site_block:{dto.block_id}', ip=dto.ip)
        return Done()


@register_scenario('admin_site_blocks_order', dto=OrderDTO, response=BlockList)
class ReorderBlocks(BaseScenario):
    """Порядок блоков: передаётся полный список id в нужной последовательности."""
    async def execute(self, dto):
        current = {b.id for b in await _all(self._db)}
        if set(dto.ids) != current or len(dto.ids) != len(current):
            raise ValidationError('Порядок должен содержать все блоки страницы')
        for position, block_id in enumerate(dto.ids):
            await self._db.update('site_blocks', block_id, {'position': position})
        await audit(self._db, dto.actor_id, 'site_blocks_order', 'site_blocks', {'ids': dto.ids}, dto.ip)
        return BlockList(items=await _all(self._db))
