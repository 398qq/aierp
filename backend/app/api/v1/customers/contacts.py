from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_perm
from app.database import get_db
from app.models.customer import CustomerContact
from app.schemas.common import fail, ok

from .crud import ContactCreate, ContactUpdate

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("/{customer_id}/contacts")
async def list_contacts(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "read")),
):
    rows = (
        (
            await db.execute(
                select(CustomerContact).where(
                    CustomerContact.customer_id == customer_id,
                    CustomerContact.deleted_at.is_(None),
                )
            )
        )
        .scalars()
        .all()
    )
    return ok(
        [
            {
                "id": c.id,
                "name": c.name,
                "title": c.title,
                "role": c.role,
                "phone": c.phone,
                "email": c.email,
                "wechat": c.wechat,
                "is_primary": c.is_primary,
                "notes": c.notes,
            }
            for c in rows
        ]
    )


@router.post("/{customer_id}/contacts", status_code=201)
async def create_contact(
    customer_id: int,
    body: ContactCreate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "write")),
):
    contact = CustomerContact(customer_id=customer_id, **body.model_dump())
    db.add(contact)
    await db.flush()
    return ok({"id": contact.id, "name": contact.name})


@router.put("/{customer_id}/contacts/{contact_id}")
async def update_contact(
    customer_id: int,
    contact_id: int,
    body: ContactUpdate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "write")),
):
    result = await db.execute(
        select(CustomerContact).where(
            CustomerContact.id == contact_id,
            CustomerContact.customer_id == customer_id,
            CustomerContact.deleted_at.is_(None),
        )
    )
    contact = result.scalar_one_or_none()
    if contact is None:
        return fail("Contact not found", 404)
    for key, val in body.model_dump(exclude_unset=True).items():
        setattr(contact, key, val)
    await db.flush()
    return ok({"id": contact.id})


@router.delete("/{customer_id}/contacts/{contact_id}")
async def delete_contact(
    customer_id: int,
    contact_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "delete")),
):
    result = await db.execute(
        select(CustomerContact).where(
            CustomerContact.id == contact_id,
            CustomerContact.customer_id == customer_id,
            CustomerContact.deleted_at.is_(None),
        )
    )
    contact = result.scalar_one_or_none()
    if contact is None:
        return fail("Contact not found", 404)
    contact.deleted_at = datetime.now(timezone.utc)
    await db.flush()
    return ok(msg="deleted")


@router.put("/{customer_id}/contacts/{contact_id}/primary")
async def set_primary_contact(
    customer_id: int,
    contact_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "write")),
):
    """Set a contact as the primary contact for a customer."""
    result = await db.execute(
        select(CustomerContact).where(
            CustomerContact.id == contact_id,
            CustomerContact.customer_id == customer_id,
            CustomerContact.deleted_at.is_(None),
        )
    )
    contact = result.scalar_one_or_none()
    if contact is None:
        return fail("Contact not found", 404)

    # Unset primary flag on all other contacts for this customer
    all_contacts = (
        (
            await db.execute(
                select(CustomerContact).where(
                    CustomerContact.customer_id == customer_id,
                    CustomerContact.deleted_at.is_(None),
                )
            )
        )
        .scalars()
        .all()
    )
    for c in all_contacts:
        c.is_primary = False
    contact.is_primary = True
    await db.flush()
    return ok({"id": contact.id, "is_primary": True})
