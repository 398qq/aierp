"""PDF service tests."""

import importlib.util
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest


REPORTLAB_AVAILABLE = importlib.util.find_spec("reportlab") is not None


def test_reportlab_dependency_declared():
    with open("requirements.txt", encoding="utf-8") as req:
        assert "reportlab" in req.read()


@pytest.mark.skipif(not REPORTLAB_AVAILABLE, reason="reportlab is not installed in this environment")
def test_generate_quotation_pdf_with_smart_sections():
    from app.services.pdf_service import generate_quotation_pdf

    quotation = SimpleNamespace(
        id=1,
        quotation_no="QT202605270001",
        title="智能报价测试",
        status="sent",
        valid_until=datetime.now(timezone.utc) + timedelta(days=3),
        created_at=datetime.now(timezone.utc),
        total_amount=250,
        notes="含税含运费需二次确认",
        customer=SimpleNamespace(
            name="测试客户",
            contact_person="张三",
            phone="13800000000",
            address="深圳",
        ),
        items=[
            SimpleNamespace(
                product_name="QMI8658",
                quantity=10,
                unit_price=25,
                total_price=250,
            )
        ],
    )

    pdf = generate_quotation_pdf(quotation)

    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 1000
