"""Products module — re-exports all product-related routers and schemas."""

from fastapi import APIRouter

from app.api.v1.products.bom import bom_router, product_bom_router
from app.api.v1.products.brands import brands_router
from app.api.v1.products.crud import router as crud_router
from app.api.v1.products.customer_codes import router as customer_codes_router
from app.api.v1.products.inventories import inventories_router
from app.api.v1.products.pack_levels import router as pack_levels_router
from app.api.v1.products.list import router as list_router
from app.api.v1.products.pricing import router as pricing_router
from app.api.v1.products.suppliers import suppliers_router
from app.api.v1.products.warehouses import inventory_router, warehouses_router

# Compose the main products router from sub-routers (no prefix here;
# sub-routers already carry their own prefixes)
router = APIRouter()
router.include_router(list_router)
router.include_router(crud_router)
router.include_router(customer_codes_router)
router.include_router(pricing_router)
router.include_router(inventories_router)
router.include_router(inventory_router)
router.include_router(bom_router)
router.include_router(product_bom_router)
router.include_router(pack_levels_router)

__all__ = [
    "router",
    "bom_router",
    "product_bom_router",
    "brands_router",
    "crud_router",
    "customer_codes_router",
    "list_router",
    "pricing_router",
    "inventories_router",
    "inventory_router",
    "pack_levels_router",
    "suppliers_router",
    "warehouses_router",
]
