"""Sales services — opportunities, quotations, sales orders, delivery notes.

Split from a single 987-line ``sales_service.py`` into per-bounded-context
submodules. Each module owns one document type's CRUD + status flow.

Public surface (re-exported here for back-compat):
- :mod:`.opportunities`  — Opportunity CRUD
- :mod:`.quotations`     — Quotation CRUD + stats + send + duplicate
- :mod:`.orders`         — SalesOrder CRUD
- :mod:`.delivery_notes` — DeliveryNote CRUD + auto-deduct/lock
- :mod:`.conversions`    — quote→order, order→delivery
- :mod:`.targets`        — Sales target CRUD + stats
- :mod:`._helpers`       — search-id and item-normalize helpers
"""

from __future__ import annotations

from app.services.sales_service.delivery_notes import (
    _auto_deduct_delivery,
    _auto_lock_sales_order,
    _apply_sales_order_to_delivery_data,
    create_delivery_note,
    delete_delivery_note,
    get_delivery_note,
    list_delivery_notes,
    mark_delivery_note_paid,
    update_delivery_note,
)
from app.services.sales_service.orders import (
    create_sales_order,
    delete_sales_order,
    get_order_by_quotation,
    get_sales_order,
    list_sales_orders,
    update_sales_order,
)
from app.services.sales_service.opportunities import (
    create_opportunity,
    delete_opportunity,
    get_opportunity,
    list_opportunities,
    update_opportunity,
)
from app.services.sales_service.quotations import (
    _notify_quotation_sent,
    create_quotation,
    create_quotation_from_inquiry,
    delete_quotation,
    duplicate_quotation,
    get_quotation,
    get_quotation_stats,
    list_quotations,
    send_quotation,
    update_quotation,
    update_quotation_status,
)
from app.services.sales_service.conversions import (
    convert_order_to_delivery,
    convert_quotation_to_order,
)
from app.services.sales_service.targets import (
    create_target,
    delete_target,
    get_target,
    get_target_stats,
    get_target_summary,
    list_targets,
    update_target,
)
from app.services.sales_service._helpers import (
    _customer_search_ids,
    _normalize_quotation_items,
    _normalize_sales_order_items,
    _sales_item_ids,
)

__all__ = [
    "_customer_search_ids",
    "_sales_item_ids",
    "_normalize_quotation_items",
    "_normalize_sales_order_items",
    "list_opportunities",
    "get_opportunity",
    "create_opportunity",
    "update_opportunity",
    "delete_opportunity",
    "list_quotations",
    "get_quotation",
    "create_quotation",
    "update_quotation",
    "get_quotation_stats",
    "duplicate_quotation",
    "update_quotation_status",
    "delete_quotation",
    "send_quotation",
    "_notify_quotation_sent",
    "create_quotation_from_inquiry",
    "list_sales_orders",
    "get_sales_order",
    "get_order_by_quotation",
    "create_sales_order",
    "update_sales_order",
    "delete_sales_order",
    "list_delivery_notes",
    "get_delivery_note",
    "_apply_sales_order_to_delivery_data",
    "create_delivery_note",
    "update_delivery_note",
    "_auto_deduct_delivery",
    "_auto_lock_sales_order",
    "delete_delivery_note",
    "mark_delivery_note_paid",
    "convert_quotation_to_order",
    "convert_order_to_delivery",
    "list_targets",
    "get_target",
    "create_target",
    "update_target",
    "delete_target",
    "get_target_summary",
    "get_target_stats",
]
