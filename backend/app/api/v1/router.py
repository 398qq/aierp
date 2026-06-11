from fastapi import APIRouter

from app.api.v1 import (
    ai,
    approvals,
    auth,
    commissions,
    customers,
    dashboard,
    documents,
    export_import,
    finance,
    finance_accounts,
    integrations,
    notifications,
    permissions,
    procurement,
    products,
    public,
    reports,
    sales,
    targets,
    transactions,
    users,
)
from app.api.v1.inventory_transactions import router as inventory_transactions_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(public.router)
api_router.include_router(customers.router)
api_router.include_router(ai.router)
api_router.include_router(products.router)
api_router.include_router(products.brands_router)
api_router.include_router(products.suppliers_router)
api_router.include_router(products.warehouses_router)
api_router.include_router(inventory_transactions_router)
api_router.include_router(transactions.po_router)
api_router.include_router(transactions.ticket_router)
api_router.include_router(transactions.visit_router)
api_router.include_router(sales.router)
api_router.include_router(targets.router)
api_router.include_router(finance.router)
api_router.include_router(commissions.router)
api_router.include_router(transactions.pay_router)
api_router.include_router(notifications.router)
api_router.include_router(dashboard.router)
api_router.include_router(transactions.sample_router)
api_router.include_router(users.router)
api_router.include_router(permissions.router)
api_router.include_router(approvals.router)
api_router.include_router(procurement.router)
api_router.include_router(reports.router)
api_router.include_router(finance_accounts.router)
api_router.include_router(integrations.router)
api_router.include_router(documents.router)
api_router.include_router(export_import.router)
