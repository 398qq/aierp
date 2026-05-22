from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.customer import Customer, CustomerTag
from app.schemas.common import fail, ok

from .crud import BatchTag, TagCreate, TagUpdate

router = APIRouter(prefix="/customers", tags=["customers"])


# --- Global Tags CRUD ---

tags_router = APIRouter(prefix="/customers/tags", tags=["customer-tags"])


@tags_router.get("")
async def list_tags(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    rows = (await db.execute(
        select(CustomerTag).where(CustomerTag.deleted_at.is_(None)).order_by(CustomerTag.name)
    )).scalars().all()
    return ok([{"id": t.id, "name": t.name, "color": t.color} for t in rows])


@tags_router.post("", status_code=201)
async def create_tag(
    body: TagCreate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    tag = CustomerTag(**body.model_dump())
    db.add(tag)
    await db.flush()
    return ok({"id": tag.id, "name": tag.name, "color": tag.color})


@tags_router.put("/{tag_id}")
async def update_tag(
    tag_id: int,
    body: TagUpdate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    result = await db.execute(
        select(CustomerTag).where(CustomerTag.id == tag_id, CustomerTag.deleted_at.is_(None))
    )
    tag = result.scalar_one_or_none()
    if tag is None:
        return fail("Tag not found", 404)
    for key, val in body.model_dump(exclude_unset=True).items():
        setattr(tag, key, val)
    await db.flush()
    return ok({"id": tag.id, "name": tag.name, "color": tag.color})


@tags_router.delete("/{tag_id}")
async def delete_tag(
    tag_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
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
    _user: dict = Depends(get_current_user),
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
    return ok({"updated": len(customers), "tags_added": len(tags)})


# --- Per-customer tag linking ---

@router.get("/{customer_id}/tags")
async def get_customer_tags(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    result = await db.execute(
        select(Customer).where(Customer.id == customer_id, Customer.deleted_at.is_(None))
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        return fail("Customer not found", 404)
    return ok([{"id": t.id, "name": t.name, "color": t.color} for t in (customer.tags or [])])


@router.post("/{customer_id}/tags/{tag_id}")
async def link_tag(
    customer_id: int,
    tag_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
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
    _user: dict = Depends(get_current_user),
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