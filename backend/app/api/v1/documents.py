"""Document management — upload, list, download, delete attachments for any entity."""

import datetime
import os
import re
import uuid

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.database import get_db
from app.models.document import Document
from app.schemas.common import fail, ok

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "uploads")
ALLOWED_MIME = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "image/jpeg",
    "image/png",
    "image/gif",
    "text/csv",
    "application/vnd.ms-excel",
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

# Characters banned from user-provided filenames to prevent path traversal
_FORBIDDEN_PATH_CHARS = re.compile(r"[/\\x00]")

router = APIRouter(prefix="/documents", tags=["documents"])


def _sanitize_filename(name: str) -> str:
    """Strip path separators and null bytes from uploaded filename."""
    if not name:
        return "unnamed"
    name = _FORBIDDEN_PATH_CHARS.sub("", name)
    return name or "unnamed"


def _ensure_upload_dir():
    os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    entity_type: str = Form(...),
    entity_id: int = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    _ensure_upload_dir()

    if file.content_type and file.content_type not in ALLOWED_MIME:
        return fail(f"不支持的文件类型: {file.content_type}")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        return fail("文件大小不能超过 10MB")

    # UUID-based storage name — OS-level path traversal is impossible by design
    ext = os.path.splitext(_sanitize_filename(file.filename or "file"))[1]
    stored_name = f"{uuid.uuid4().hex}{ext}"
    stored_path = os.path.join(UPLOAD_DIR, stored_name)

    with open(stored_path, "wb") as f:
        f.write(content)

    doc = Document(
        entity_type=entity_type,
        entity_id=entity_id,
        filename=_sanitize_filename(file.filename or "unknown"),
        file_path=stored_name,
        file_size=len(content),
        mime_type=file.content_type,
        uploaded_by=current_user["user_id"],
    )
    db.add(doc)
    await db.commit()
    return ok({"id": doc.id, "filename": doc.filename}, msg="文件上传成功")


@router.get("")
async def list_documents(
    entity_type: str = Query(...),
    entity_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    result = await db.execute(
        select(Document)
        .options(selectinload(Document.uploader))
        .where(
            Document.entity_type == entity_type,
            Document.entity_id == entity_id,
            Document.deleted_at.is_(None),
        )
        .order_by(Document.id.desc())
    )
    docs = result.scalars().all()
    return ok(
        [
            {
                "id": d.id,
                "entity_type": d.entity_type,
                "entity_id": d.entity_id,
                "filename": d.filename,
                "file_size": d.file_size,
                "mime_type": d.mime_type,
                "uploaded_by": d.uploaded_by,
                "uploader_name": d.uploader.username if d.uploader else "",
                "created_at": str(d.created_at),
            }
            for d in docs
        ]
    )


@router.get("/{doc_id}/download")
async def download_document(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    doc = (
        await db.execute(
            select(Document).where(Document.id == doc_id, Document.deleted_at.is_(None))
        )
    ).scalar_one_or_none()
    if not doc:
        return fail("文件不存在")

    file_path = os.path.join(UPLOAD_DIR, doc.file_path)
    if not os.path.exists(file_path):
        return fail("文件已丢失")

    return FileResponse(
        file_path,
        filename=doc.filename,
        media_type=doc.mime_type or "application/octet-stream",
    )


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    doc = (
        await db.execute(
            select(Document).where(Document.id == doc_id, Document.deleted_at.is_(None))
        )
    ).scalar_one_or_none()
    if not doc:
        return fail("文件不存在")
    doc.deleted_at = datetime.datetime.now(datetime.timezone.utc)

    # Also remove the physical file
    file_path = os.path.join(UPLOAD_DIR, doc.file_path)
    try:
        os.remove(file_path)
    except OSError:
        pass

    await db.commit()
    return ok(msg="文件已删除")
