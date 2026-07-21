"""Customer-specific product codes (customer part numbers)."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.customer import Customer
from app.models.product import CustomerProductCode, Product
from app.schemas.common import fail, ok

router = APIRouter(prefix="/products", tags=["products:customer-codes"])


class CustomerProductCodeIn(BaseModel):
    customer_id: int
    customer_part_no: str = Field(min_length=1, max_length=150)
    customer_product_name: str | None = Field(None, max_length=255)
    is_active: bool = True
    notes: str | None = None


class CustomerProductCodeUpdate(BaseModel):
    customer_part_no: str | None = Field(None, min_length=1, max_length=150)
    customer_product_name: str | None = Field(None, max_length=255)
    is_active: bool | None = None
    notes: str | None = None


def _serialize(link: CustomerProductCode, customer_name: str | None = None) -> dict:
    return {
        "id": link.id,
        "customer_id": link.customer_id,
        "customer_name": customer_name,
        "product_id": link.product_id,
        "customer_part_no": link.customer_part_no,
        "customer_product_name": link.customer_product_name,
        "is_active": link.is_active,
        "notes": link.notes,
        "created_at": link.created_at,
        "updated_at": link.updated_at,
    }


async def _validate_refs(
    db: AsyncSession, product_id: int, customer_id: int
) -> tuple[Product | None, Customer | None]:
    product = await db.get(Product, product_id)
    customer = await db.get(Customer, customer_id)
    if product and product.deleted_at is not None:
        product = None
    if customer and customer.deleted_at is not None:
        customer = None
    return product, customer


async def _find_conflict(
    db: AsyncSession,
    *,
    customer_id: int,
    product_id: int,
    customer_part_no: str,
    exclude_id: int | None = None,
) -> str | None:
    filters = [
        CustomerProductCode.deleted_at.is_(None),
        CustomerProductCode.customer_id == customer_id,
        or_(
            CustomerProductCode.product_id == product_id,
            func.lower(CustomerProductCode.customer_part_no)
            == customer_part_no.lower(),
        ),
    ]
    if exclude_id is not None:
        filters.append(CustomerProductCode.id != exclude_id)
    existing = await db.scalar(select(CustomerProductCode.id).where(*filters))
    if existing is None:
        return None
    return "该客户已维护此产品或客户料号已被其他产品占用"


@router.get("/{product_id}/customer-codes")
async def list_customer_product_codes(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    rows = (
        await db.execute(
            select(CustomerProductCode, Customer.name)
            .join(Customer, Customer.id == CustomerProductCode.customer_id)
            .where(
                CustomerProductCode.product_id == product_id,
                CustomerProductCode.deleted_at.is_(None),
                Customer.deleted_at.is_(None),
            )
            .order_by(Customer.name, CustomerProductCode.id)
        )
    ).all()
    return ok([_serialize(link, customer_name) for link, customer_name in rows])


@router.post("/{product_id}/customer-codes")
async def create_customer_product_code(
    product_id: int,
    body: CustomerProductCodeIn,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    product, customer = await _validate_refs(db, product_id, body.customer_id)
    if product is None:
        return fail("产品不存在", 404)
    if customer is None:
        return fail("客户不存在", 404)
    part_no = body.customer_part_no.strip()
    conflict = await _find_conflict(
        db,
        customer_id=body.customer_id,
        product_id=product_id,
        customer_part_no=part_no,
    )
    if conflict:
        return fail(conflict, 409)
    link = CustomerProductCode(
        product_id=product_id,
        customer_id=body.customer_id,
        customer_part_no=part_no,
        customer_product_name=(body.customer_product_name or "").strip() or None,
        is_active=body.is_active,
        notes=body.notes,
        created_by=user["user_id"],
    )
    db.add(link)
    await db.commit()
    await db.refresh(link)
    return ok(_serialize(link, customer.name))


@router.put("/{product_id}/customer-codes/{link_id}")
async def update_customer_product_code(
    product_id: int,
    link_id: int,
    body: CustomerProductCodeUpdate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    link = await db.scalar(
        select(CustomerProductCode).where(
            CustomerProductCode.id == link_id,
            CustomerProductCode.product_id == product_id,
            CustomerProductCode.deleted_at.is_(None),
        )
    )
    if link is None:
        return fail("客户料号映射不存在", 404)
    values = body.model_dump(exclude_unset=True)
    part_no = str(values.get("customer_part_no", link.customer_part_no)).strip()
    conflict = await _find_conflict(
        db,
        customer_id=link.customer_id,
        product_id=product_id,
        customer_part_no=part_no,
        exclude_id=link.id,
    )
    if conflict:
        return fail(conflict, 409)
    if "customer_part_no" in values:
        values["customer_part_no"] = part_no
    if "customer_product_name" in values:
        values["customer_product_name"] = (
            str(values["customer_product_name"] or "").strip() or None
        )
    for key, value in values.items():
        setattr(link, key, value)
    link.updated_by = user["user_id"]
    await db.commit()
    await db.refresh(link)
    customer_name = await db.scalar(
        select(Customer.name).where(Customer.id == link.customer_id)
    )
    return ok(_serialize(link, customer_name))


@router.delete("/{product_id}/customer-codes/{link_id}")
async def delete_customer_product_code(
    product_id: int,
    link_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    link = await db.scalar(
        select(CustomerProductCode).where(
            CustomerProductCode.id == link_id,
            CustomerProductCode.product_id == product_id,
            CustomerProductCode.deleted_at.is_(None),
        )
    )
    if link is None:
        return fail("客户料号映射不存在", 404)
    link.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    return ok({"deleted": True})
