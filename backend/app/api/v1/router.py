from fastapi import APIRouter

from app.api.v1 import ai, auth, customers, dashboard, finance, notifications, products, sales, targets, transactions

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(customers.router)
api_router.include_router(customers.tags_router)
api_router.include_router(ai.router)
api_router.include_router(products.router)
api_router.include_router(products.brands_router)
api_router.include_router(products.suppliers_router)
api_router.include_router(products.warehouses_router)
api_router.include_router(products.inventory_router)
api_router.include_router(transactions.po_router)
api_router.include_router(transactions.pay_router)
api_router.include_router(transactions.ticket_router)
api_router.include_router(transactions.visit_router)
api_router.include_router(sales.router)
api_router.include_router(targets.router)
api_router.include_router(finance.router)
api_router.include_router(notifications.router)
api_router.include_router(dashboard.router)
api_router.include_router(transactions.sample_router)
