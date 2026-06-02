"""Shared domain infrastructure — events, errors, base types."""

from app.domain.shared.errors import DomainError
from app.domain.shared.events import DomainEvent

__all__ = ["DomainError", "DomainEvent"]
