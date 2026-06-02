"""Tests for domain shared layer — pure unit tests, no DB."""

import pytest

from app.domain.shared.errors import (
    BusinessRuleViolation,
    ConcurrentModificationError,
    DomainError,
    InsufficientStockError,
    InvalidStateTransition,
    NotFoundError,
)


class TestDomainErrors:
    def test_domain_error_carries_context(self):
        exc = DomainError("boom", foo="bar", count=3)
        assert exc.message == "boom"
        assert exc.context == {"foo": "bar", "count": 3}
        assert exc.code == "DOMAIN_ERROR"
        assert exc.http_status == 400

    def test_business_rule_violation_default_status(self):
        exc = BusinessRuleViolation("rule broken")
        assert exc.http_status == 422
        assert exc.code == "BUSINESS_RULE_VIOLATION"

    def test_invalid_state_transition(self):
        exc = InvalidStateTransition("draft → shipped not allowed")
        assert exc.http_status == 422
        assert exc.code == "INVALID_STATE_TRANSITION"

    def test_not_found(self):
        exc = NotFoundError("customer 99 not found")
        assert exc.http_status == 404
        assert exc.code == "NOT_FOUND"

    def test_concurrent_modification(self):
        exc = ConcurrentModificationError("conflict")
        assert exc.http_status == 409
        assert exc.code == "CONCURRENT_MODIFICATION"

    def test_insufficient_stock_includes_inventory_context(self):
        exc = InsufficientStockError(product_id=42, requested=100, available=30)
        assert "42" in exc.message
        assert "100" in exc.message
        assert "30" in exc.message
        assert exc.context == {"product_id": 42, "requested": 100, "available": 30}
        assert exc.http_status == 422
        assert exc.code == "INSUFFICIENT_STOCK"

    def test_to_payload_serializes_correctly(self):
        exc = InsufficientStockError(product_id=1, requested=10, available=5)
        payload = exc.to_payload()
        assert payload["code"] == "INSUFFICIENT_STOCK"
        assert payload["msg"].startswith("库存不足")
        assert payload["product_id"] == 1

    def test_can_be_raised_and_caught_as_domain_error(self):
        with pytest.raises(DomainError) as ei:
            raise InsufficientStockError(product_id=1, requested=10, available=5)
        assert ei.value.code == "INSUFFICIENT_STOCK"
