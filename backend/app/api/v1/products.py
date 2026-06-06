"""Product & inventory management API — backward compatibility shim.

All endpoints have been moved to submodules under app.api.v1.products/.
This file re-exports all sub-routers and schemas for backward compatibility.
"""

from fastapi import APIRouter

from app.api.v1.products import (
    brands_router,
    crud_router,
    inventories_router,
    inventory_router,
    list_router,
    pricing_router,
    suppliers_router,
    warehouses_router,
)
from app.api.v1.products.brands import BrandBatchUpdate, BrandCreate, BrandUpdate
from app.api.v1.products.crud import (
    BatchAdjustBody,
    BatchAdjustItem,
    InventoryCreate,
    InventoryUpdate,
    ProductCreate,
    ProductUpdate,
    SupplierProductLink,
)
from app.api.v1.products.pricing import PriceImportBody, PriceImportItem

# Main router — no prefix here; sub-routers already have their own prefixes
# so paths resolve correctly when mounted at /products
router = APIRouter()
router.include_router(list_router)
router.include_router(crud_router)
router.include_router(pricing_router)
router.include_router(inventories_router)
router.include_router(inventory_router)

__all__ = [
    "router",
    "brands_router",
    "crud_router",
    "list_router",
    "pricing_router",
    "inventories_router",
    "inventory_router",
    "suppliers_router",
    "warehouses_router",
    # Schemas
    "ProductCreate",
    "ProductUpdate",
    "BrandCreate",
    "BrandUpdate",
    "SupplierProductLink",
    "InventoryCreate",
    "InventoryUpdate",
    "PriceImportItem",
    "PriceImportBody",
    "BatchAdjustItem",
    "BatchAdjustBody",
    "BrandBatchUpdate",
]
