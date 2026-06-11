import os
import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_perm
from app.database import get_db
from app.models.customer import CustomerAttachment
from app.schemas.common import fail, ok

from .crud import UPLOAD_DIR

router = APIRouter(prefix="/customers", tags=["customers"])

_FORBIDDEN_FILENAME_CHARS = re.compile(r"[/\\\x00\r\n]")


def _safe_filename(name: str) -> str:
    """Strip path separators and null bytes from user-supplied filename."""
    if not name:
        return "unnamed"
    name = _FORBIDDEN_FILENAME_CHARS.sub("", name)
    return name or "unnamed"


@router.get("/{customer_id}/attachments")
async def list_attachments(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "read")),
):
    rows = (
        (
            await db.execute(
                select(CustomerAttachment)
                .where(
                    CustomerAttachment.customer_id == customer_id,
                    CustomerAttachment.deleted_at.is_(None),
                )
                .order_by(CustomerAttachment.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    return ok(
        [
            {
                "id": a.id,
                "original_name": a.original_name,
                "file_size": a.file_size,
                "content_type": a.content_type,
                "category": a.category,
                "created_at": str(a.created_at) if a.created_at else None,
            }
            for a in rows
        ]
    )


@router.post("/{customer_id}/attachments", status_code=201)
async def upload_attachment(
    customer_id: int,
    file: UploadFile = File(...),
    category: str = Query("contract"),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "write")),
):
    if not file.filename:
        return fail("No file selected", 400)

    ext = os.path.splitext(_safe_filename(file.filename))[1]
    stored_name = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(UPLOAD_DIR, stored_name)

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        return fail("File size cannot exceed 10MB", 400)
    with open(file_path, "wb") as f:
        f.write(content)

    attachment = CustomerAttachment(
        customer_id=customer_id,
        filename=stored_name,
        original_name=_safe_filename(file.filename),
        file_size=len(content),
        content_type=file.content_type,
        category=category,
    )
    db.add(attachment)
    await db.flush()

    return ok(
        {
            "id": attachment.id,
            "original_name": attachment.original_name,
            "file_size": attachment.file_size,
        }
    )


@router.get("/{customer_id}/attachments/{attachment_id}/download")
async def download_attachment(
    customer_id: int,
    attachment_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "read")),
):
    result = await db.execute(
        select(CustomerAttachment).where(
            CustomerAttachment.id == attachment_id,
            CustomerAttachment.customer_id == customer_id,
            CustomerAttachment.deleted_at.is_(None),
        )
    )
    attachment = result.scalar_one_or_none()
    if attachment is None:
        return fail("Attachment not found", 404)

    file_path = os.path.join(UPLOAD_DIR, attachment.filename)
    if not os.path.exists(file_path):
        return fail("File not found on disk", 404)

    return FileResponse(
        file_path,
        filename=attachment.original_name,
        media_type=attachment.content_type or "application/octet-stream",
    )


@router.delete("/{customer_id}/attachments/{attachment_id}")
async def delete_attachment(
    customer_id: int,
    attachment_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("customers", "delete")),
):
    result = await db.execute(
        select(CustomerAttachment).where(
            CustomerAttachment.id == attachment_id,
            CustomerAttachment.customer_id == customer_id,
            CustomerAttachment.deleted_at.is_(None),
        )
    )
    attachment = result.scalar_one_or_none()
    if attachment is None:
        return fail("Attachment not found", 404)

    file_path = os.path.join(UPLOAD_DIR, attachment.filename)
    if os.path.exists(file_path):
        os.remove(file_path)

    attachment.deleted_at = datetime.now(timezone.utc)
    await db.flush()
    return ok(msg="deleted")
