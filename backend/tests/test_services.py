"""Unit tests for business logic services and core utilities."""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class DbResult:
    """Sync result mock for db.execute() responses. Methods are callable and return the configured value."""

    def __init__(self, **methods):
        for name, value in methods.items():
            setattr(self, name, value if callable(value) else (lambda v=value: v))


class Db:
    """Mock AsyncSession with sequential db.execute() results."""

    def __init__(self, *results):
        self._results = list(results)
        self.execute = AsyncMock(side_effect=self._results)


class TestPricingService:
    @pytest.mark.unit
    async def test_match_supplier_to_products_supplier_not_found(self):
        from app.services.pricing_service import match_supplier_to_products

        db = Db(DbResult(scalar_one_or_none=lambda: None))
        with pytest.raises(ValueError, match="Supplier not found"):
            await match_supplier_to_products(db, supplier_id=999)

    @pytest.mark.unit
    async def test_match_supplier_to_products_no_catalog_text(self):
        from app.services.pricing_service import match_supplier_to_products

        db = Db(DbResult(scalar_one_or_none=lambda: MagicMock(product_lines=None)))
        result = await match_supplier_to_products(db, supplier_id=1)
        assert result == []

    @pytest.mark.unit
    async def test_match_supplier_to_products_empty_catalog(self):
        from app.services.pricing_service import match_supplier_to_products

        db = Db(DbResult(scalar_one_or_none=lambda: MagicMock(product_lines="   ")))
        result = await match_supplier_to_products(db, supplier_id=1)
        assert result == []

    @pytest.mark.unit
    async def test_match_supplier_to_products_no_products_in_system(self):
        from app.services.pricing_service import match_supplier_to_products

        db = Db(
            DbResult(scalar_one_or_none=lambda: MagicMock(product_lines="STM32 MCU")),
            DbResult(all=lambda: []),
        )
        result = await match_supplier_to_products(db, supplier_id=1)
        assert result == []

    @pytest.mark.unit
    async def test_match_supplier_to_products_with_catalog_text_param(self):
        from app.services.pricing_service import match_supplier_to_products

        products = [(1, "SKU1", "Product A", "Cat1", "0805", "Brand A", "品牌A")]
        db = Db(
            DbResult(scalar_one_or_none=lambda: MagicMock(product_lines="old text")),
            DbResult(all=lambda: products),
        )
        with patch("app.services.ai.client.ai_client") as mock_ai:
            mock_ai.chat_structured = AsyncMock(return_value={"matches": []})
            result = await match_supplier_to_products(
                db, supplier_id=1, catalog_text="override text"
            )
            assert result == []
            user_msg = mock_ai.chat_structured.call_args[0][0][1]["content"]
            assert "override text" in user_msg

    @pytest.mark.unit
    async def test_get_pricing_benchmark_empty_data(self):
        from app.services.pricing_service import get_pricing_benchmark

        db = Db(
            DbResult(all=lambda: []), DbResult(all=lambda: []), DbResult(all=lambda: [])
        )
        result = await get_pricing_benchmark(db, product_id=1)
        assert result["product_id"] == 1
        assert result["sales_history"]["count"] == 0
        assert result["active_quotations"]["count"] == 0
        assert result["supplier_costs"]["count"] == 0

    @pytest.mark.unit
    async def test_pricing_benchmark_stats_calculation(self):
        from app.services.pricing_service import get_pricing_benchmark
        from collections import namedtuple

        PriceRow = namedtuple("PriceRow", ["unit_price", "quantity", "created_at"])
        QuoteRow = namedtuple("QuoteRow", ["unit_price", "quantity"])
        SupplierRow = namedtuple(
            "SupplierRow", ["cost_price", "lead_time_days", "moq", "name"]
        )

        db = Db(
            DbResult(all=lambda: [PriceRow(10.0, 100, "2025-01-01")]),
            DbResult(all=lambda: [QuoteRow(12.0, 50)]),
            DbResult(all=lambda: [SupplierRow(8.0, 14, 1000, "Supplier A")]),
        )
        result = await get_pricing_benchmark(db, product_id=1)
        assert result["sales_history"]["count"] == 1
        assert result["sales_history"]["stats"]["min"] == 10.0
        assert result["supplier_costs"]["count"] == 1
        assert result["supplier_costs"]["suppliers"][0]["name"] == "Supplier A"

    @pytest.mark.unit
    async def test_recommend_price_product_not_found(self):
        from app.services.pricing_service import recommend_price

        db = Db(
            DbResult(first=lambda: None),
            DbResult(all=lambda: []),  # second call, not reached
        )
        with pytest.raises(ValueError, match="Product not found"):
            await recommend_price(db, product_id=999)

    @pytest.mark.unit
    async def test_recommend_price_success(self):
        from app.services.pricing_service import recommend_price
        from collections import namedtuple

        SupplierRow = namedtuple("SupplierRow", ["cost_price", "lead_time_days", "moq"])
        db = Db(
            DbResult(first=lambda: ("SKU1", "Product A", "Cat", "Brand", "品牌")),
            DbResult(all=lambda: [SupplierRow(5.0, 7, 100)]),
            DbResult(scalar=lambda: 100),
        )
        with patch("app.services.ai.client.ai_client") as mock_ai:
            mock_ai.chat_structured = AsyncMock(
                return_value={
                    "recommended_price": 12.5,
                    "price_range": [10, 15],
                    "margin_pct": 60.0,
                    "confidence": "high",
                    "rationale": "Good market.",
                    "negotiation_floor": 9.0,
                    "upsell_suggestion": None,
                }
            )
            result = await recommend_price(db, product_id=1, quantity=100)
            assert result["recommended_price"] == 12.5
            assert result["margin_pct"] == 60.0
            assert "context" in result

    @pytest.mark.unit
    async def test_recommend_price_market_condition_out_of_stock(self):
        from app.services.pricing_service import recommend_price
        from collections import namedtuple

        SupplierRow = namedtuple("SupplierRow", ["cost_price", "lead_time_days", "moq"])
        db = Db(
            DbResult(first=lambda: ("SKU1", "Product A", "Cat", "Brand", "品牌")),
            DbResult(all=lambda: [SupplierRow(5.0, 7, 100)]),
            DbResult(scalar=lambda: 0),
        )
        with patch("app.services.ai.client.ai_client") as mock_ai:
            mock_ai.chat_structured = AsyncMock(
                return_value={
                    "recommended_price": None,
                    "price_range": [],
                    "margin_pct": 0,
                    "confidence": "low",
                    "rationale": "Out of stock.",
                    "negotiation_floor": None,
                    "upsell_suggestion": None,
                }
            )
            result = await recommend_price(db, product_id=1)
            assert result["context"]["market_condition"] == "缺货"


class TestSecurity:
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_hash_and_verify_password(self):
        from app.core.security import hash_password, verify_password

        hashed = hash_password("mypassword")
        assert hashed != "mypassword"
        assert await verify_password("mypassword", hashed) is True
        assert await verify_password("wrongpassword", hashed) is False

    @pytest.mark.unit
    def test_create_and_decode_token(self):
        from app.core.security import create_access_token, decode_access_token

        token = create_access_token(user_id=42, username="test")
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == "42"
        assert payload["username"] == "test"

    @pytest.mark.unit
    def test_decode_invalid_token(self):
        from app.core.security import decode_access_token

        assert decode_access_token("garbage.token.here") is None
        assert decode_access_token("") is None


class TestSalesAIService:
    @pytest.mark.unit
    def test_paginated_response_preserves_ai_enrichment(self):
        from app.schemas.common import PageData

        page = PageData[dict](
            list=[{"id": 7}],
            total=1,
            page=1,
            page_size=20,
            ai={7: {"delivery_risk": "medium", "flag": None}},
        )

        assert page.model_dump()["ai"] == {
            7: {"delivery_risk": "medium", "flag": None}
        }

    @pytest.mark.unit
    async def test_order_detail_ai_timeout_returns_safe_fallback(self, monkeypatch):
        from datetime import date
        from app.services import sales_ai_service

        class SlowAIClient:
            async def chat_structured(self, *_args, **_kwargs):
                await asyncio.sleep(1)

        order = MagicMock(
            total_amount=13800,
            status="confirmed",
            order_date=date(2026, 6, 17),
            delivery_date=date(2026, 6, 17),
            notes="",
            items=[MagicMock()],
        )
        monkeypatch.setattr(sales_ai_service, "SALES_AI_TIMEOUT_SECONDS", 0.01)
        with patch("app.services.ai.client.ai_client", SlowAIClient()):
            result = await sales_ai_service.enrich_sales_order(MagicMock(), order)

        assert result is not None
        assert result["fallback"] is True
        assert result["delivery_risk"] in {"medium", "high"}
        assert result["health_score"] < 80
        assert result["flags"]

    @pytest.mark.unit
    async def test_order_list_ai_timeout_falls_back_fast(self, monkeypatch):
        from app.services import sales_ai_service

        class SlowAIClient:
            async def chat_structured(self, *_args, **_kwargs):
                await asyncio.sleep(1)
                return {
                    "items": [
                        {"id": 1, "delivery_risk": "low", "flag": None}
                    ]
                }

        order = MagicMock(id=1, total_amount=100, status="pending", items=[])
        monkeypatch.setattr(sales_ai_service, "SALES_AI_TIMEOUT_SECONDS", 0.01)
        with patch("app.services.ai.client.ai_client", SlowAIClient()):
            started = time.perf_counter()
            result = await sales_ai_service.enrich_order_list(MagicMock(), [order])

        assert time.perf_counter() - started < 0.5
        assert result == {1: {"delivery_risk": "low", "flag": None}}

    @pytest.mark.unit
    async def test_order_list_ai_accepts_cached_serialized_orders(self, monkeypatch):
        from app.services import sales_ai_service

        async def fake_cached_ai_call(*_args, **_kwargs):
            return {
                "items": [
                    {"id": 7, "delivery_risk": "medium", "flag": None}
                ]
            }

        monkeypatch.setattr(sales_ai_service, "_cached_ai_call", fake_cached_ai_call)
        cached_order = {
            "id": 7,
            "total_amount": "6101.00",
            "status": "confirmed",
            "items": [{"id": 70}],
        }

        result = await sales_ai_service.enrich_order_list(
            MagicMock(), [cached_order]
        )

        assert result == {7: {"delivery_risk": "medium", "flag": None}}
