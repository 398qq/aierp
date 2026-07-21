"""Integration endpoints — e-commerce import, logistics tracking, webhooks."""

import csv
import io

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.permissions import require_perm
from app.database import get_db
from app.models.account import IntegrationConfig
from app.models.customer import Customer
from app.models.product import Product
from app.models.sales import SalesOrder, SalesOrderItem
from app.schemas.common import fail, ok
from app.services.customer_service import find_name_conflict
from app.services.sales_service._helpers import _apply_customer_product_codes

router = APIRouter(prefix="/integrations", tags=["integrations"])


# ---------------------------------------------------------------------------
# Integration Configs
# ---------------------------------------------------------------------------
@router.get("/configs")
async def list_configs(
    type: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("system", "read")),
):
    q = select(IntegrationConfig).where(IntegrationConfig.deleted_at.is_(None))
    if type:
        q = q.where(IntegrationConfig.type == type)
    result = await db.execute(q.order_by(IntegrationConfig.id))
    configs = result.scalars().all()
    return ok(
        [
            {
                "id": c.id,
                "type": c.type,
                "name": c.name,
                "endpoint": c.endpoint,
                "settings": c.settings,
                "enabled": c.enabled,
                "created_at": str(c.created_at),
            }
            for c in configs
        ]
    )


class ConfigCreate(BaseModel):
    type: str
    name: str
    api_key: str = ""
    api_secret: str = ""
    endpoint: str = ""
    settings: dict = {}
    enabled: bool = False


@router.post("/configs", status_code=201)
async def create_config(
    body: ConfigCreate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("system", "write")),
):
    c = IntegrationConfig(
        type=body.type,
        name=body.name,
        api_key_encrypted=body.api_key or None,
        api_secret_encrypted=body.api_secret or None,
        endpoint=body.endpoint or None,
        settings=body.settings,
        enabled=body.enabled,
    )
    db.add(c)
    await db.commit()
    return ok({"id": c.id}, msg="集成配置创建成功")


@router.put("/configs/{config_id}")
async def update_config(
    config_id: int,
    body: ConfigCreate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("system", "write")),
):
    c = (
        await db.execute(
            select(IntegrationConfig).where(
                IntegrationConfig.id == config_id,
                IntegrationConfig.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if not c:
        return fail("配置不存在")
    c.type = body.type
    c.name = body.name
    c.api_key_encrypted = body.api_key or None
    c.api_secret_encrypted = body.api_secret or None
    c.endpoint = body.endpoint or None
    c.settings = body.settings
    c.enabled = body.enabled
    await db.commit()
    return ok(msg="配置更新成功")


@router.delete("/configs/{config_id}")
async def delete_config(
    config_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_perm("system", "write")),
):
    c = (
        await db.execute(
            select(IntegrationConfig).where(
                IntegrationConfig.id == config_id,
                IntegrationConfig.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if not c:
        return fail("配置不存在")
    import datetime

    c.deleted_at = datetime.datetime.now(datetime.timezone.utc)
    await db.commit()
    return ok(msg="配置已删除")


# ---------------------------------------------------------------------------
# E-commerce Order Import
# ---------------------------------------------------------------------------
@router.post("/orders/import")
async def import_orders(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_perm("sales", "write")),
):
    """Import orders from CSV (e.g. Taobao/1688 export)."""
    content = await file.read()
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
    rows = list(reader)

    created_orders = 0
    created_customers = 0
    errors = []

    for i, row in enumerate(rows):
        try:
            buyer_name = row.get("buyer_name", row.get("买家", f"导入客户_{i}"))
            buyer_phone = row.get("buyer_phone", row.get("电话", ""))
            product_sku = row.get("sku", row.get("商家编码", ""))
            qty = int(row.get("quantity", row.get("数量", 1)))
            price = float(row.get("price", row.get("单价", 0)))

            # Find or create customer
            customer = await find_name_conflict(db, buyer_name)
            if not customer:
                customer = (
                    (
                        await db.execute(
                            select(Customer).where(
                                Customer.name == buyer_name,
                                Customer.deleted_at.is_(None),
                            )
                        )
                    )
                    .scalars()
                    .first()
                )
            if not customer:
                customer = Customer(name=buyer_name, phone=buyer_phone)
                db.add(customer)
                await db.flush()
                created_customers += 1

            # Find product by SKU
            product = None
            if product_sku:
                product = (
                    (
                        await db.execute(
                            select(Product).where(
                                Product.sku == product_sku, Product.deleted_at.is_(None)
                            )
                        )
                    )
                    .scalars()
                    .first()
                )

            # Create sales order
            order = SalesOrder(
                customer_id=customer.id,
                order_no=f"IMP-{i + 1:04d}",
                total_amount=qty * price,
                status="draft",
            )
            db.add(order)
            await db.flush()

            if product:
                item_data = {
                    "product_id": product.id,
                    "product_name": product.name,
                    "quantity": qty,
                    "unit_price": price,
                    "total_price": qty * price,
                }
                await _apply_customer_product_codes(
                    db, customer.id, [item_data]
                )
                db.add(SalesOrderItem(order_id=order.id, **item_data))

            created_orders += 1
        except Exception as e:
            errors.append(f"行 {i + 1}: {str(e)}")

    await db.commit()
    return ok(
        {
            "created_orders": created_orders,
            "created_customers": created_customers,
            "total_rows": len(rows),
            "errors": errors,
        }
    )


# ---------------------------------------------------------------------------
# Logistics Tracking
# ---------------------------------------------------------------------------
@router.get("/logistics/{tracking_no}")
async def track_logistics(
    tracking_no: str,
    provider: str = Query("cainiao"),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Query logistics tracking info. Currently returns stub; integrate with real API."""
    # Check if we have a PO with this tracking number
    from app.models.transaction import PurchaseOrder

    po = (
        (
            await db.execute(
                select(PurchaseOrder).where(
                    PurchaseOrder.logistics_no == tracking_no,
                    PurchaseOrder.deleted_at.is_(None),
                )
            )
        )
        .scalars()
        .first()
    )

    return ok(
        {
            "tracking_no": tracking_no,
            "provider": provider,
            "linked_po": {"id": po.id, "order_no": po.order_no, "status": po.status}
            if po
            else None,
            "traces": [],  # Stub — integrate with real logistics API
            "note": "物流API未配置，请先在 集成配置 中设置物流服务商",
        }
    )


# ---------------------------------------------------------------------------
# Webhook Receiver (HMAC-SHA256 signed)
# ---------------------------------------------------------------------------
@router.post("/webhook/{source}")
async def receive_webhook(
    source: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Receive webhook payloads from external systems.

    All webhooks must be signed with HMAC-SHA256:
    - Header X-AIERP-Signature: hex(HMAC-SHA256(secret, f"{ts}.{body}"))
    - Header X-AIERP-Timestamp: Unix epoch seconds (must be within 5 min)

    Configure the secret per source via env var WEBHOOK_SECRET_<SOURCE>.
    See app/core/webhook_security.py for the protocol details.
    """
    from app.core.webhook_security import require_webhook_signature

    # Verify signature manually since `source` comes from path params
    body = await require_webhook_signature(
        request,
        source=source,
        x_aierp_signature=request.headers.get("X-AIERP-Signature"),
        x_aierp_timestamp=request.headers.get("X-AIERP-Timestamp"),
    )

    import json

    try:
        body_json = json.loads(body) if body else {}
    except json.JSONDecodeError:
        return fail("Invalid JSON body", 400)

    from app.models.finance import Notification
    from app.models.user import User

    admin = (
        (await db.execute(select(User).where(User.role == "admin").limit(1)))
        .scalars()
        .first()
    )
    if admin:
        db.add(
            Notification(
                user_id=admin.id,
                type="webhook",
                title=f"Webhook: {source}",
                content=json.dumps(body_json)[:500],
                channel="in_app",
            )
        )

    await db.commit()
    return ok({"received": True, "source": source})
