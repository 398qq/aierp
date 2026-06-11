"""PDF service tests."""

import os
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest


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


def test_generate_quotation_pdf_prefers_embeddable_chinese_font_when_available():
    if not os.path.exists("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"):
        pytest.skip("WenQuanYi font is not installed in this environment")

    from app.services import pdf_service
    from app.services.pdf_service import generate_quotation_pdf

    if not pdf_service.REPORTLAB_AVAILABLE:
        pytest.skip("ReportLab is not installed in this environment")

    quotation = SimpleNamespace(
        id=1,
        quotation_no="QT202605270002",
        title="中文字体覆盖测试",
        status="sent",
        valid_until=datetime.now(timezone.utc) + timedelta(days=3),
        created_at=datetime.now(timezone.utc),
        total_amount=250,
        notes="加工工艺、零件、辅料、付款方式、报价有效期",
        customer=SimpleNamespace(
            name="测试客户有限公司",
            contact_person="张三",
            phone="13800000000",
            address="深圳市南山区科技园",
        ),
        items=[
            SimpleNamespace(
                product_name="全局产品名称：连接器、电阻、电容、芯片、辅料",
                quantity=10,
                unit_price=25,
                total_price=250,
            )
        ],
    )

    pdf = generate_quotation_pdf(quotation)

    assert b"WenQuanYiMicroHei" in pdf
    assert b"IPAPGothic" not in pdf


def test_money_upper_cn_formats_quote_amounts():
    from app.services.pdf_service import _money_upper_cn

    assert _money_upper_cn(0) == "零元整"
    assert _money_upper_cn(10001) == "壹万零壹元整"
    assert _money_upper_cn(1234567.89) == "壹佰贰拾叁万肆仟伍佰陆拾柒元捌角玖分"


def test_generate_sales_order_pdf_with_smart_sections():
    from app.services.pdf_service import generate_sales_order_pdf

    order = SimpleNamespace(
        id=1,
        order_no="SO202605290001",
        status="confirmed",
        order_date=datetime.now(timezone.utc),
        delivery_date=datetime.now(timezone.utc) + timedelta(days=5),
        total_amount=500,
        notes="分两批交付",
        quotation_id=12,
        customer=SimpleNamespace(
            name="测试客户",
            contact_person="李四",
            phone="13900000000",
            address="上海",
        ),
        items=[
            SimpleNamespace(
                product_name="STM32F103",
                quantity=20,
                unit_price=25,
                total_price=500,
            )
        ],
    )

    pdf = generate_sales_order_pdf(order)

    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 1000
