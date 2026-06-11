"""Domain exceptions — business rule violations, state errors, concurrency conflicts."""

from typing import Any


class DomainError(Exception):
    """Base for all business/domain exceptions.

    Carries an error code, HTTP status mapping, and arbitrary context for the API layer.
    """

    code: str = "DOMAIN_ERROR"
    http_status: int = 400

    def __init__(self, message: str, **context: Any) -> None:
        super().__init__(message)
        self.message = message
        self.context = context

    def to_payload(self) -> dict:
        return {"code": self.code, "msg": self.message, **self.context}


class BusinessRuleViolation(DomainError):
    """Generic business rule failure (422)."""

    code = "BUSINESS_RULE_VIOLATION"
    http_status = 422


class InvalidStateTransition(DomainError):
    """State machine forbids this transition (422)."""

    code = "INVALID_STATE_TRANSITION"
    http_status = 422


class NotFoundError(DomainError):
    """Aggregate not found (404)."""

    code = "NOT_FOUND"
    http_status = 404


class InsufficientStockError(BusinessRuleViolation):
    code = "INSUFFICIENT_STOCK"

    def __init__(self, product_id: int, requested: int, available: int) -> None:
        super().__init__(
            f"库存不足: 产品 {product_id}, 需要 {requested}, 可用 {available}",
            product_id=product_id,
            requested=requested,
            available=available,
        )


class ConcurrentModificationError(DomainError):
    code = "CONCURRENT_MODIFICATION"
    http_status = 409


class ValidationError(DomainError):
    """Input validation failure (422). Use when field-level validation fails."""

    code = "VALIDATION_ERROR"
    http_status = 422


class ConflictError(DomainError):
    """Conflict with current resource state (e.g. duplicate key) (409)."""

    code = "CONFLICT"
    http_status = 409
