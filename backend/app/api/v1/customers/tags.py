from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_perm
from app.database import get_db
from app.models.customer import Customer, CustomerTag
from app.schemas.common import fail, ok
from app.services.cache_service import cache_bump_version

from .crud import BatchTag, TagCreate, TagUpdate

router = APIRouter(prefix="/customers", tags=["customers"])


# --- Global Tags CRUD ---

tags_router = APIRouter(prefix="/customers/tags", tags=["customer-tags"])

DEFAULT_CUSTOMER_TAGS = [
    {"name": "重点客户", "color": "gold"},
    {"name": "潜在客户", "color": "blue"},
    {"name": "样品跟进", "color": "cyan"},
    {"name": "价格敏感", "color": "orange"},
    {"name": "风险预警", "color": "red"},
]


def _tag_payload(tag: CustomerTag) -> dict:
    return {"id": tag.id, "name": tag.name, "color": tag.color}


async def _find_tag_by_name(db: AsyncSession, name: str) -> CustomerTag | None:
    result = await db.execute(select(CustomerTag).where(func.lower(CustomerTag.name) == name.lower()))
    return result.scalars().first()


async def _create_or_restore_tag(db: AsyncSession, name: str, color: str | None) -> tuple[CustomerTag, bool]:
    tag = await _find_tag_by_name(db, name)
    if tag is not None:
        restored = tag.deleted_at is not None
        tag.deleted_at = None
        tag.name = name
        tag.color = color
        return tag, restored

    tag = CustomerTag(name=name, color=color)
    db.add(tag)
    await db.flush()
    return tag, True


@tags_router.get("")
async def list_tags(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "read")),
):
    rows = (await db.execute(
        select(CustomerTag).where(CustomerTag.deleted_at.is_(None)).order_by(CustomerTag.name)
    )).scalars().all()
    return ok([_tag_payload(t) for t in rows])


@tags_router.post("", status_code=201)
async def create_tag(
    body: TagCreate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "write")),
):
    name = body.name.strip()
    if not name:
        return fail("Tag name required", 400)

    existing = await _find_tag_by_name(db, name)
    if existing is not None and existing.deleted_at is None:
        return fail("Tag already exists", 409)
    if existing is not None:
        existing.deleted_at = None
        existing.name = name
        existing.color = body.color
        await db.flush()
        return ok(_tag_payload(existing))

    tag = CustomerTag(name=name, color=body.color)
    db.add(tag)
    await db.flush()
    return ok(_tag_payload(tag))


@tags_router.post("/defaults", status_code=201)
async def generate_default_tags(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "write")),
):
    tags: list[CustomerTag] = []
    created = 0
    for item in DEFAULT_CUSTOMER_TAGS:
        tag, was_created = await _create_or_restore_tag(db, item["name"], item["color"])
        tags.append(tag)
        if was_created:
            created += 1
    await db.flush()
    return ok({
        "created": created,
        "existing": len(DEFAULT_CUSTOMER_TAGS) - created,
        "tags": [_tag_payload(tag) for tag in tags],
    })


@tags_router.put("/{tag_id}")
async def update_tag(
    tag_id: int,
    body: TagUpdate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "write")),
):
    result = await db.execute(
        select(CustomerTag).where(CustomerTag.id == tag_id, CustomerTag.deleted_at.is_(None))
    )
    tag = result.scalar_one_or_none()
    if tag is None:
        return fail("Tag not found", 404)
    for key, val in body.model_dump(exclude_unset=True).items():
        if key == "name" and isinstance(val, str):
            val = val.strip()
            if not val:
                return fail("Tag name required", 400)
            duplicate = await _find_tag_by_name(db, val)
            if duplicate is not None and duplicate.id != tag.id and duplicate.deleted_at is None:
                return fail("Tag already exists", 409)
        setattr(tag, key, val.strip() if key == "name" and isinstance(val, str) else val)
    await db.flush()
    return ok(_tag_payload(tag))


@tags_router.delete("/{tag_id}")
async def delete_tag(
    tag_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "delete")),
):
    result = await db.execute(
        select(CustomerTag).where(CustomerTag.id == tag_id, CustomerTag.deleted_at.is_(None))
    )
    tag = result.scalar_one_or_none()
    if tag is None:
        return fail("Tag not found", 404)
    tag.deleted_at = datetime.now(timezone.utc)
    await db.flush()
    return ok(msg="deleted")


# --- Batch tag operations ---

@router.post("/batch-tag")
async def batch_tag(
    body: BatchTag,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "write")),
):
    if not body.ids or not body.tag_ids:
        return fail("ids and tag_ids required", 400)
    customers_result = await db.execute(
        select(Customer).where(Customer.id.in_(body.ids), Customer.deleted_at.is_(None))
    )
    customers = customers_result.scalars().all()
    tags_result = await db.execute(
        select(CustomerTag).where(CustomerTag.id.in_(body.tag_ids), CustomerTag.deleted_at.is_(None))
    )
    tags = tags_result.scalars().all()
    for c in customers:
        for t in tags:
            if t not in c.tags:
                c.tags.append(t)
    await db.flush()
    await cache_bump_version("customers:list")
    return ok({"updated": len(customers), "tags_added": len(tags)})


# --- Per-customer tag linking ---

@router.get("/{customer_id}/tags")
async def get_customer_tags(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "read")),
):
    result = await db.execute(
        select(Customer).where(Customer.id == customer_id, Customer.deleted_at.is_(None))
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        return fail("Customer not found", 404)
    return ok([_tag_payload(t) for t in (customer.tags or [])])


@router.post("/{customer_id}/tags/{tag_id}")
async def link_tag(
    customer_id: int,
    tag_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "write")),
):
    result = await db.execute(
        select(Customer).where(Customer.id == customer_id, Customer.deleted_at.is_(None))
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        return fail("Customer not found", 404)
    tag_result = await db.execute(
        select(CustomerTag).where(CustomerTag.id == tag_id, CustomerTag.deleted_at.is_(None))
    )
    tag = tag_result.scalar_one_or_none()
    if tag is None:
        return fail("Tag not found", 404)
    if tag not in customer.tags:
        customer.tags.append(tag)
        await db.flush()
    return ok({"tag_id": tag_id})


@router.delete("/{customer_id}/tags/{tag_id}")
async def unlink_tag(
    customer_id: int,
    tag_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "write")),
):
    result = await db.execute(
        select(Customer).where(Customer.id == customer_id, Customer.deleted_at.is_(None))
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        return fail("Customer not found", 404)
    tag_result = await db.execute(
        select(CustomerTag).where(CustomerTag.id == tag_id, CustomerTag.deleted_at.is_(None))
    )
    tag = tag_result.scalar_one_or_none()
    if tag is None:
        return fail("Tag not found", 404)
    if tag in customer.tags:
        customer.tags.remove(tag)
        await db.flush()
    return ok(msg="unlinked")
