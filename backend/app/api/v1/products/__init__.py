"""Products module — re-exports all product-related routers and schemas."""

from fastapi import APIRouter

from app.api.v1.products.brands import brands_router
from app.api.v1.products.crud import router as crud_router
from app.api.v1.products.inventories import inventories_router
from app.api.v1.products.list import router as list_router
from app.api.v1.products.pricing import router as pricing_router
from app.api.v1.products.suppliers import suppliers_router
from app.api.v1.products.warehouses import inventory_router, warehouses_router

# Compose the main products router from sub-routers (no prefix here;
# sub-routers already carry their own prefixes)
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
]
