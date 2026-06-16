"""Customer API tests."""

import csv
import io
from datetime import datetime, timedelta, timezone

from httpx import AsyncClient


class TestCustomers:
    """Customer CRUD + batch operations."""

    async def test_list_empty(self, async_client: AsyncClient, auth_headers: dict):
        resp = await async_client.get("/api/v1/customers", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_list_requires_customer_read_permission(
        self, async_client: AsyncClient, db_session
    ):
        from app.core.security import create_access_token, hash_password
        from app.models.user import User

        user = User(
            username="customer-no-access",
            password=hash_password("NoAccess123!"),
            role="guest",
        )
        db_session.add(user)
        await db_session.flush()
        from app.services.cache_service import cache_delete

        await cache_delete(f"perm:{user.id}:customers:read")
        token = create_access_token(user.id, user.username)

        resp = await async_client.get(
            "/api/v1/customers",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert resp.status_code == 403

    async def test_list_returns_status_and_total_amount(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        customer = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "列表汇总客户", "status": "active"},
        )
        customer_id = customer.json()["data"]["id"]
        await async_client.post(
            "/api/v1/sales-orders",
            headers=auth_headers,
            json={
                "customer_id": customer_id,
                "status": "pending",
                "total_amount": 12345.67,
                "items": [
                    {
                        "product_name": "列表汇总产品",
                        "quantity": 1,
                        "unit_price": 12345.67,
                        "total_price": 12345.67,
                    }
                ],
            },
        )

        resp = await async_client.get(
            "/api/v1/customers?q=列表汇总客户",
            headers=auth_headers,
        )

        assert resp.status_code == 200
        row = resp.json()["data"]["list"][0]
        assert row["status"] == "active"
        assert row["total_amount"] == 12345.67

    async def test_list_rejects_unbounded_page_size(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        resp = await async_client.get(
            "/api/v1/customers?page_size=501",
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_create_customer(self, async_client: AsyncClient, auth_headers: dict):
        resp = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "测试客户", "type": "终端客户", "industry": "工业"},
        )
        assert resp.status_code == 201
        assert resp.json()["code"] == 0
        assert "id" in resp.json()["data"]
        assert resp.json()["data"]["created_at"]

        cid = resp.json()["data"]["id"]
        detail = await async_client.get(
            f"/api/v1/customers/{cid}", headers=auth_headers
        )
        assert detail.json()["data"]["created_at"]

        customers = await async_client.get("/api/v1/customers", headers=auth_headers)
        row = next(
            item for item in customers.json()["data"]["list"] if item["id"] == cid
        )
        assert row["created_at"]

    async def test_create_customer_auto_generates_short_name(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        resp = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "深圳市星河电子有限公司", "type": "终端客户"},
        )
        assert resp.status_code == 201
        cid = resp.json()["data"]["id"]

        detail = await async_client.get(
            f"/api/v1/customers/{cid}", headers=auth_headers
        )
        assert detail.status_code == 200
        assert detail.json()["data"]["short_name"] == "深圳市星河电子"

    async def test_create_customer_keeps_manual_short_name(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        resp = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={
                "name": "上海星河电子有限公司",
                "short_name": "星河",
                "type": "终端客户",
            },
        )
        assert resp.status_code == 201
        cid = resp.json()["data"]["id"]

        detail = await async_client.get(
            f"/api/v1/customers/{cid}", headers=auth_headers
        )
        assert detail.status_code == 200
        assert detail.json()["data"]["short_name"] == "星河"

    async def test_create_customer_rejects_duplicate_normalized_name(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        first = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "深圳市华芯科技有限公司", "type": "终端客户"},
        )
        second = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "深圳华芯科技", "type": "终端客户"},
        )

        assert first.status_code == 201
        assert second.status_code == 400
        assert second.json()["code"] == 400
        assert "客户名称已存在" in second.json()["msg"]

        listed = await async_client.get(
            "/api/v1/customers?q=华芯科技", headers=auth_headers
        )
        assert listed.json()["data"]["total"] == 1

    async def test_update_customer_rejects_duplicate_normalized_name(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        first = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "上海市星河电子有限公司"},
        )
        second = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "北京远航贸易有限公司"},
        )
        second_id = second.json()["data"]["id"]

        resp = await async_client.put(
            f"/api/v1/customers/{second_id}",
            headers=auth_headers,
            json={"name": "上海星河电子"},
        )

        assert first.status_code == 201
        assert second.status_code == 201
        assert resp.status_code == 400
        assert "客户名称已存在" in resp.json()["msg"]

        detail = await async_client.get(
            f"/api/v1/customers/{second_id}", headers=auth_headers
        )
        assert detail.json()["data"]["name"] == "北京远航贸易有限公司"

    async def test_import_customers_rejects_duplicate_normalized_name(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "广州市明芯半导体有限公司"},
        )
        csv_data = "名称,编码\n广州明芯半导体,CUST-HN-990001\n".encode()

        resp = await async_client.post(
            "/api/v1/customers/import",
            headers=auth_headers,
            files={"file": ("customers.csv", csv_data, "text/csv")},
        )

        assert resp.status_code == 400
        assert "客户名称已存在" in resp.json()["msg"]

        listed = await async_client.get(
            "/api/v1/customers?q=明芯半导体", headers=auth_headers
        )
        assert listed.json()["data"]["total"] == 1

    async def test_create_customer_rejects_duplicate_code_number(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        first = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "编码数字客户A", "code": "CUST-HD-000123"},
        )
        second = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "编码数字客户B", "code": "CUST-HN-123"},
        )

        assert first.status_code == 201
        assert second.status_code == 400
        assert second.json()["code"] == 400
        assert "数字部分已存在" in second.json()["msg"]

        listed = await async_client.get(
            "/api/v1/customers?q=编码数字客户", headers=auth_headers
        )
        assert listed.json()["data"]["total"] == 1

    async def test_update_customer_rejects_duplicate_code_number(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        first = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "编码更新客户A", "code": "CUST-HD-000456"},
        )
        second = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "编码更新客户B", "code": "CUST-HN-000457"},
        )
        second_id = second.json()["data"]["id"]

        resp = await async_client.put(
            f"/api/v1/customers/{second_id}",
            headers=auth_headers,
            json={"code": "CUST-XN-456"},
        )

        assert first.status_code == 201
        assert second.status_code == 201
        assert resp.status_code == 400
        assert "数字部分已存在" in resp.json()["msg"]

        detail = await async_client.get(
            f"/api/v1/customers/{second_id}", headers=auth_headers
        )
        assert detail.json()["data"]["code"] == "CUST-HN-000457"

    async def test_import_customers_rejects_duplicate_code_number(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "编码导入客户A", "code": "CUST-HD-000789"},
        )
        csv_data = "名称,编码\n编码导入客户B,CUST-HN-789\n".encode()

        resp = await async_client.post(
            "/api/v1/customers/import",
            headers=auth_headers,
            files={"file": ("customers.csv", csv_data, "text/csv")},
        )

        assert resp.status_code == 400
        assert "数字部分已存在" in resp.json()["msg"]

        listed = await async_client.get(
            "/api/v1/customers?q=编码导入客户", headers=auth_headers
        )
        assert listed.json()["data"]["total"] == 1

    async def test_get_customer(self, async_client: AsyncClient, auth_headers: dict):
        c = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "单个客户", "type": "终端客户"},
        )
        cid = c.json()["data"]["id"]
        resp = await async_client.get(f"/api/v1/customers/{cid}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["name"] == "单个客户"

    async def test_get_customer_quotation_history(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        customer = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "报价历史客户", "type": "终端客户"},
        )
        other = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "其他报价客户", "type": "终端客户"},
        )
        customer_id = customer.json()["data"]["id"]
        other_id = other.json()["data"]["id"]

        won = await async_client.post(
            "/api/v1/quotations",
            headers=auth_headers,
            json={
                "customer_id": customer_id,
                "status": "won",
                "total_amount": 1200,
                "items": [
                    {
                        "product_name": "QMI8658",
                        "quantity": 10,
                        "unit_price": 120,
                        "total_price": 1200,
                    }
                ],
            },
        )
        sent = await async_client.post(
            "/api/v1/quotations",
            headers=auth_headers,
            json={
                "customer_id": customer_id,
                "status": "sent",
                "total_amount": 600,
                "items": [
                    {
                        "product_name": "WK2212",
                        "quantity": 3,
                        "unit_price": 200,
                        "total_price": 600,
                    }
                ],
            },
        )
        await async_client.post(
            "/api/v1/quotations",
            headers=auth_headers,
            json={
                "customer_id": other_id,
                "status": "won",
                "total_amount": 9999,
                "items": [
                    {
                        "product_name": "OTHER",
                        "quantity": 1,
                        "unit_price": 9999,
                        "total_price": 9999,
                    }
                ],
            },
        )

        resp = await async_client.get(
            f"/api/v1/customers/{customer_id}/quotation-history", headers=auth_headers
        )

        assert resp.status_code == 200
        payload = resp.json()
        assert payload["code"] == 0
        assert payload["data"]["total"] == 2
        assert payload["data"]["stats"]["won"] == 1
        assert payload["data"]["stats"]["pending"] == 1
        assert payload["data"]["stats"]["total_won_amount"] == 1200
        ids = {item["id"] for item in payload["data"]["quotations"]}
        assert ids == {won.json()["data"]["id"], sent.json()["data"]["id"]}

    async def test_get_customer_quotation_history_status_filter(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        customer = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "报价状态筛选客户", "type": "终端客户"},
        )
        customer_id = customer.json()["data"]["id"]
        await async_client.post(
            "/api/v1/quotations",
            headers=auth_headers,
            json={"customer_id": customer_id, "status": "won", "total_amount": 1200},
        )
        await async_client.post(
            "/api/v1/quotations",
            headers=auth_headers,
            json={"customer_id": customer_id, "status": "sent", "total_amount": 600},
        )

        resp = await async_client.get(
            f"/api/v1/customers/{customer_id}/quotation-history?status=sent",
            headers=auth_headers,
        )

        assert resp.status_code == 200
        payload = resp.json()["data"]
        assert payload["total"] == 1
        assert payload["quotations"][0]["status"] == "sent"

    async def test_update_customer(self, async_client: AsyncClient, auth_headers: dict):
        c = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "原始", "type": "终端客户"},
        )
        cid = c.json()["data"]["id"]
        resp = await async_client.put(
            f"/api/v1/customers/{cid}",
            headers=auth_headers,
            json={"name": "已更新"},
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_compliance_fields_create_and_update(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """2026-06-16: 开票/收款字段 (tax_id/registration_number/invoice_title/invoice_address/bank_name/bank_account) 应可写入并读出。"""
        compliance = {
            "tax_id": "91441900MACDGJQL79",
            "registration_number": "91441900MACDGJQL79",
            "invoice_title": "测试公司有限公司",
            "invoice_address": "广东省东莞市塘厦镇测试路1号",
            "bank_name": "招商银行东莞塘厦支行",
            "bank_account": "6225880123456789",
        }

        # Create 时写入
        c = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "测试合规字段客户", "type": "终端客户", **compliance},
        )
        assert c.status_code == 201, c.text
        cid = c.json()["data"]["id"]

        # GET 验证字段都写入
        detail = await async_client.get(
            f"/api/v1/customers/{cid}", headers=auth_headers
        )
        body = detail.json()["data"]
        for k, v in compliance.items():
            assert body[k] == v, f"{k}: 期望 {v!r}, 实际 {body[k]!r}"

        # PUT 更新字段（部分更新）
        partial = {"bank_name": "工商银行塘厦支行", "bank_account": "6222021234567890"}
        resp = await async_client.put(
            f"/api/v1/customers/{cid}", headers=auth_headers, json=partial
        )
        assert resp.status_code == 200, resp.text

        detail2 = await async_client.get(
            f"/api/v1/customers/{cid}", headers=auth_headers
        )
        body2 = detail2.json()["data"]
        assert body2["bank_name"] == "工商银行塘厦支行"
        assert body2["bank_account"] == "6222021234567890"
        # 其他字段保持不变
        assert body2["tax_id"] == "91441900MACDGJQL79"
        assert body2["invoice_title"] == "测试公司有限公司"

    async def test_delete_customer(self, async_client: AsyncClient, auth_headers: dict):
        c = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "待删除", "type": "终端客户"},
        )
        cid = c.json()["data"]["id"]
        resp = await async_client.delete(
            f"/api/v1/customers/{cid}", headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_batch_delete(self, async_client: AsyncClient, auth_headers: dict):
        c1 = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "批量删1", "type": "终端客户"},
        )
        c2 = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "批量删2", "type": "终端客户"},
        )
        ids = [c1.json()["data"]["id"], c2.json()["data"]["id"]]
        resp = await async_client.post(
            "/api/v1/customers/batch-delete",
            headers=auth_headers,
            json={"ids": ids},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["deleted"] == 2

    async def test_export_selected_customers_only(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        first = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "导出选中客户A"},
        )
        await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "导出选中客户B"},
        )
        selected_id = first.json()["data"]["id"]

        resp = await async_client.get(
            f"/api/v1/customers/export?ids={selected_id}",
            headers=auth_headers,
        )

        assert resp.status_code == 200
        rows = list(csv.reader(io.StringIO(resp.text)))
        names = [row[0] for row in rows[1:]]
        assert names == ["导出选中客户A"]

    async def test_duplicate_detection_ignores_weak_name_overlap(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "上海星辰科技有限公司", "phone": "13800000001"},
        )
        await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "上海星河科技有限公司", "phone": "13800000002"},
        )

        resp = await async_client.get(
            "/api/v1/customers/duplicates", headers=auth_headers
        )

        assert resp.status_code == 200
        assert resp.json()["data"]["pairs"] == []

    async def test_duplicate_detection_matches_normalized_legal_name(
        self, async_client: AsyncClient, auth_headers: dict, db_session
    ):
        from app.models.customer import Customer

        db_session.add_all(
            [
                Customer(name="深圳市华芯科技有限公司"),
                Customer(name="深圳华芯科技"),
            ]
        )
        await db_session.flush()

        resp = await async_client.get(
            "/api/v1/customers/duplicates", headers=auth_headers
        )

        assert resp.status_code == 200
        pairs = resp.json()["data"]["pairs"]
        assert len(pairs) == 1
        assert pairs[0]["similarity"] == 1
        assert "名称完全一致" in pairs[0]["reasons"]

    async def test_duplicate_detection_requires_related_name_for_same_email(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "杭州明芯电子有限公司", "email": "sales@example.com"},
        )
        await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "杭州明芯电子科技有限公司", "email": "sales@example.com"},
        )
        await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "北京远航贸易有限公司", "email": "sales@example.com"},
        )

        resp = await async_client.get(
            "/api/v1/customers/duplicates", headers=auth_headers
        )

        assert resp.status_code == 200
        pairs = resp.json()["data"]["pairs"]
        assert len(pairs) == 1
        names = {pairs[0]["customer_a"]["name"], pairs[0]["customer_b"]["name"]}
        assert names == {"杭州明芯电子有限公司", "杭州明芯电子科技有限公司"}
        assert "邮箱一致" in pairs[0]["reasons"]

    async def test_unauthorized(self, async_client: AsyncClient):
        resp = await async_client.get("/api/v1/customers")
        assert resp.status_code == 401

    async def test_ai_recognize_customer(
        self, async_client: AsyncClient, auth_headers: dict, monkeypatch
    ):
        async def fake_recognize_customer(text: str, ocr_candidates=None):
            assert "深圳市星河电子有限公司" in text
            return {
                "name": "深圳市星河电子有限公司",
                "short_name": "星河电子",
                "customer_type": "OEM",
                "industry": "汽车电子",
                "level": "A",
                "region": "华南",
                "source": "展会",
                "contact_person": "张工",
                "phone": "13800001111",
                "email": "zhang@example.com",
                "owner": "王明",
                "credit_limit": 200000,
                "credit_level": "A",
                "address": "深圳市南山区",
                "notes": "展会线索",
                "confidence": 0.9,
                "summary": "识别为华南汽车电子OEM客户",
            }

        monkeypatch.setattr(
            "app.api.v1.ai.customer.recognition.CustomerAgent.recognize_customer",
            fake_recognize_customer,
        )

        resp = await async_client.post(
            "/api/v1/ai/customer/recognition",
            headers=auth_headers,
            json={
                "text": "深圳市星河电子有限公司，汽车电子OEM，联系人张工，13800001111，展会线索。"
            },
        )

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["name"] == "深圳市星河电子有限公司"
        assert data["customer_type"] == "OEM"
        assert data["industry"] == "汽车电子"
        assert data["region"] == "华南"
        assert data["credit_limit"] == 200000
        assert data["confidence"] == 0.9

    async def test_ai_recognize_business_card(
        self, async_client: AsyncClient, auth_headers: dict, monkeypatch
    ):
        def fake_extract_business_card_ocr(content: bytes):
            assert content == b"fake-card-image"
            return {
                "text": "深圳市星河电子有限公司\n张工 13800001111\nzhang@example.com\n汽车电子OEM",
                "engine": "rapidocr",
                "confidence": 0.91,
                "score": 3.2,
                "image_quality": {
                    "width": 1280,
                    "height": 720,
                    "megapixels": 0.92,
                    "brightness": 128,
                    "contrast": 52,
                    "sharpness": 24,
                    "warnings": [],
                },
                "candidates": [
                    {
                        "engine": "rapidocr",
                        "confidence": 0.91,
                        "score": 3.2,
                        "text_length": 55,
                    }
                ],
                "candidate_texts": [
                    {
                        "engine": "rapidocr:original",
                        "confidence": 0.91,
                        "score": 3.2,
                        "text_length": 55,
                        "key_hits": ["phone", "email", "company"],
                        "text": "深圳市星河电子有限公司\n张工 13800001111\nzhang@example.com",
                    },
                    {
                        "engine": "rapidocr:gray_autocontrast",
                        "confidence": 0.86,
                        "score": 2.8,
                        "text_length": 34,
                        "key_hits": ["address"],
                        "text": "地址: 深圳市南山区科技园",
                    },
                ],
            }

        async def fake_recognize_customer(text: str, ocr_candidates=None):
            assert "张工" in text
            assert ocr_candidates
            assert ocr_candidates[0]["engine"] == "rapidocr:original"
            assert "深圳市南山区科技园" in ocr_candidates[1]["text"]
            return {
                "name": "深圳市星河电子有限公司",
                "short_name": "星河电子",
                "customer_type": "OEM",
                "industry": "汽车电子",
                "level": "A",
                "region": "华南",
                "source": "展会",
                "contact_person": "张工",
                "phone": "13800001111",
                "email": "zhang@example.com",
                "owner": "",
                "credit_limit": None,
                "credit_level": "",
                "address": "",
                "notes": "名片识别线索",
                "confidence": 0.88,
                "summary": "已从名片识别客户资料",
            }

        monkeypatch.setattr(
            "app.api.v1.ai.customer._ocr.extract_business_card_ocr",
            fake_extract_business_card_ocr,
        )
        monkeypatch.setattr(
            "app.api.v1.ai.customer.recognition.CustomerAgent.recognize_customer",
            fake_recognize_customer,
        )

        resp = await async_client.post(
            "/api/v1/ai/customer/card-recognition",
            headers=auth_headers,
            files={"file": ("card.png", b"fake-card-image", "image/png")},
        )

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["name"] == "深圳市星河电子有限公司"
        assert data["contact_person"] == "张工"
        assert data["raw_text"].startswith("深圳市星河电子有限公司")
        assert data["ocr_engine"] == "rapidocr"
        assert data["ocr_confidence"] == 0.91
        assert data["ocr_score"] == 3.2
        assert data["ocr_candidates"][0]["engine"] == "rapidocr"
        assert data["image_quality"]["width"] == 1280
        assert data["recognition_warnings"] == []

    async def test_ai_recognize_business_card_accepts_body_file(
        self, async_client: AsyncClient, auth_headers: dict, monkeypatch
    ):
        def fake_extract_business_card_ocr(content: bytes):
            assert content == b"fake-card-image"
            return {
                "text": "深圳市星河电子有限公司\n张工 13800001111",
                "engine": "tesseract",
                "confidence": 0,
            }

        async def fake_recognize_customer(text: str, ocr_candidates=None):
            return {
                "name": "深圳市星河电子有限公司",
                "short_name": "星河电子",
                "customer_type": "OEM",
                "industry": "汽车电子",
                "level": "A",
                "region": "华南",
                "source": "展会",
                "contact_person": "张工",
                "phone": "13800001111",
                "email": "",
                "owner": "",
                "credit_limit": None,
                "credit_level": "",
                "address": "",
                "notes": "",
                "confidence": 0.88,
                "summary": "已从名片识别客户资料",
            }

        monkeypatch.setattr(
            "app.api.v1.ai.customer._ocr.extract_business_card_ocr",
            fake_extract_business_card_ocr,
        )
        monkeypatch.setattr(
            "app.api.v1.ai.customer.recognition.CustomerAgent.recognize_customer",
            fake_recognize_customer,
        )

        resp = await async_client.post(
            "/api/v1/ai/customer/card-recognition",
            headers=auth_headers,
            files={"body.file": ("card.png", b"fake-card-image", "image/png")},
        )

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["name"] == "深圳市星河电子有限公司"

    async def test_ai_recognize_business_card_returns_missing_field_warnings(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        monkeypatch,
    ):
        def fake_extract_business_card_ocr(content: bytes):
            return {
                "text": "张工 13800001111",
                "engine": "rapidocr:original",
                "confidence": 0.42,
                "score": 0.8,
                "image_quality": {
                    "width": 420,
                    "height": 260,
                    "megapixels": 0.11,
                    "brightness": 30,
                    "contrast": 12,
                    "sharpness": 8,
                    "warnings": ["名片图片分辨率偏低，建议使用更清晰的原图"],
                },
                "candidates": [
                    {
                        "engine": "rapidocr:original",
                        "confidence": 0.42,
                        "score": 0.8,
                        "text_length": 14,
                    }
                ],
            }

        async def fake_recognize_customer(text: str, ocr_candidates=None):
            return {
                "name": "",
                "short_name": "",
                "customer_type": "",
                "industry": "",
                "level": "",
                "region": "",
                "source": "",
                "contact_person": "张工",
                "phone": "13800001111",
                "email": "",
                "owner": "",
                "credit_limit": None,
                "credit_level": "",
                "address": "",
                "notes": "",
                "confidence": 0.4,
                "summary": "部分识别",
            }

        monkeypatch.setattr(
            "app.api.v1.ai.customer._ocr.extract_business_card_ocr",
            fake_extract_business_card_ocr,
        )
        monkeypatch.setattr(
            "app.api.v1.ai.customer.recognition.CustomerAgent.recognize_customer",
            fake_recognize_customer,
        )

        resp = await async_client.post(
            "/api/v1/ai/customer/card-recognition",
            headers=auth_headers,
            files={"file": ("card.png", b"fake-card-image", "image/png")},
        )

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "未识别到客户名称" in data["recognition_warnings"]
        assert "未识别到邮箱" in data["recognition_warnings"]
        assert (
            "OCR评分较低，建议上传更清晰、无遮挡的名片图片"
            in data["recognition_warnings"]
        )
        assert (
            "名片图片分辨率偏低，建议使用更清晰的原图" in data["recognition_warnings"]
        )

    def test_business_card_image_quality_flags_low_quality_image(self):
        from PIL import Image

        from app.api.v1.ai.customer._ocr import _analyze_business_card_image_quality

        image = Image.new("RGB", (360, 220), (20, 20, 20))
        quality = _analyze_business_card_image_quality(image)

        assert quality["width"] == 360
        assert quality["height"] == 220
        assert "名片图片分辨率偏低，建议使用更清晰的原图" in quality["warnings"]
        assert "图片偏暗，建议补光或提高曝光后重拍" in quality["warnings"]

    def test_opencv_business_card_region_variant_crops_rotated_card(self):
        import pytest
        from PIL import Image, ImageDraw

        pytest.importorskip("cv2")

        from app.api.v1.ai.customer._ocr_regions import (
            _opencv_business_card_region_variants,
        )

        background = Image.new("RGB", (1200, 800), (80, 80, 80))
        card = Image.new("RGB", (760, 430), "white")
        draw = ImageDraw.Draw(card)
        draw.rectangle((0, 0, 759, 429), outline="black", width=8)
        draw.text((60, 80), "Shenzhen Xinghe Electronics Co., Ltd.", fill="black")
        draw.text((60, 160), "Zhang 13800001111", fill="black")
        rotated = card.rotate(8, expand=True, fillcolor=(80, 80, 80))
        background.paste(rotated, (220, 170))

        variants = _opencv_business_card_region_variants(background)

        assert variants
        name, cropped = variants[0]
        assert name.startswith("opencv_card_")
        assert 650 <= cropped.width <= 850
        assert 360 <= cropped.height <= 500

    def test_business_card_ocr_scoring_prefers_field_rich_text(self):
        from app.api.v1.ai.customer._ocr_merging import _merge_card_ocr_results

        result = _merge_card_ocr_results(
            [
                {
                    "text": "AAAA BBBB CCCC DDDD EEEE FFFF GGGG HHHH IIII JJJJ KKKK LLLL",
                    "engine": "rapidocr:original",
                    "confidence": 0.95,
                },
                {
                    "text": "深圳市星河电子有限公司\n张工 13800001111\nzhang@example.com",
                    "engine": "rapidocr:gray_autocontrast",
                    "confidence": 0.72,
                },
            ]
        )

        assert result["engine"] == "rapidocr:gray_autocontrast"
        assert result["text"].startswith("深圳市星河电子有限公司")
        assert result["score"] > 0
        assert len(result["candidates"]) == 2

    def test_business_card_ocr_merge_keeps_key_fields_from_other_candidates(self):
        from app.api.v1.ai.customer._ocr_merging import _merge_card_ocr_results

        result = _merge_card_ocr_results(
            [
                {
                    "text": "深圳市星河电子有限公司\n张工 13800001111\nzhang@example.com",
                    "engine": "rapidocr:original",
                    "confidence": 0.6,
                },
                {
                    "text": "深圳市星河电子有限公司\n销售经理\n地址: 深圳市南山区科技园\n官网 www.example.com\n主营电子元器件代理销售",
                    "engine": "rapidocr:threshold_190",
                    "confidence": 0.96,
                },
            ]
        )

        assert result["engine"] == "rapidocr:original"
        assert "13800001111" in result["text"]
        assert "zhang@example.com" in result["text"]
        assert "深圳市南山区科技园" in result["text"]
        assert result["candidate_texts"][0]["engine"] == "rapidocr:original"
        assert "text" in result["candidate_texts"][0]

    def test_easyocr_result_is_normalized_as_ocr_candidate(self, monkeypatch):
        from PIL import Image

        from app.api.v1.ai.customer import _ocr_engines as customer_ai

        class FakeEasyOCRReader:
            def readtext(self, image, detail=1, paragraph=False):
                assert detail == 1
                assert paragraph is False
                assert image.shape[:2] == (120, 240)
                return [
                    (
                        [[0, 0], [10, 0], [10, 10], [0, 10]],
                        "深圳市星河电子有限公司",
                        0.92,
                    ),
                    ([[0, 20], [10, 20], [10, 30], [0, 30]], "张工 13800001111", 0.86),
                    ([[0, 40], [10, 40], [10, 50], [0, 50]], "zhang@example.com", 0.88),
                ]

        monkeypatch.setattr(
            customer_ai, "_get_easyocr_reader", lambda: FakeEasyOCRReader()
        )

        result = customer_ai.ocr_with_easyocr(Image.new("RGB", (240, 120), "white"))

        assert result["engine"] == "easyocr"
        assert result["confidence"] == 0.8867
        assert "深圳市星河电子有限公司" in result["text"]
        assert "13800001111" in result["text"]
        assert "zhang@example.com" in result["text"]

    def test_business_card_ocr_selection_prefers_easyocr_when_key_fields_match(self):
        from app.api.v1.ai.customer._ocr_merging import _merge_card_ocr_results

        result = _merge_card_ocr_results(
            [
                {
                    "text": "深圳市星河电子有限公司\n张工 13800001111\nzhang@example.com",
                    "engine": "rapidocr:original",
                    "confidence": 0.96,
                },
                {
                    "text": "深圳市星河电子有限公司\n张工 13800001111\nzhang@example.com",
                    "engine": "easyocr:opencv_card_wide_closed_50_150",
                    "confidence": 0.72,
                },
            ]
        )

        assert result["engine"] == "easyocr:opencv_card_wide_closed_50_150"
        assert (
            result["candidate_texts"][0]["engine"]
            == "easyocr:opencv_card_wide_closed_50_150"
        )

    def test_extract_business_card_ocr_runs_easyocr_before_rapidocr(self, monkeypatch):
        import io

        from PIL import Image

        from app.api.v1.ai.customer import _ocr as customer_ai
        from app.api.v1.ai.customer import _ocr_engines as customer_ocr_engines

        calls = []

        monkeypatch.setattr(
            customer_ocr_engines,
            "opencv_business_card_region_variants",
            lambda image: [],
        )

        def fake_easyocr(image):
            calls.append("easyocr")
            return {
                "text": "深圳市星河电子有限公司\n张工 13800001111\nzhang@example.com",
                "engine": "easyocr",
                "confidence": 0.8,
            }

        def fake_rapidocr(image):
            calls.append("rapidocr")
            return {
                "text": "深圳市星河电子有限公司\n张工 13800001111",
                "engine": "rapidocr",
                "confidence": 0.9,
            }

        monkeypatch.setattr(customer_ocr_engines, "ocr_with_easyocr", fake_easyocr)
        monkeypatch.setattr(customer_ocr_engines, "ocr_with_rapidocr", fake_rapidocr)
        monkeypatch.setattr(
            customer_ocr_engines,
            "ocr_with_tesseract",
            lambda image: {"text": "", "engine": "tesseract", "confidence": 0},
        )

        image = Image.new("RGB", (900, 500), "white")
        content = io.BytesIO()
        image.save(content, format="PNG")

        result = customer_ai._extract_business_card_ocr(content.getvalue())

        assert calls[0] == "easyocr"
        assert "rapidocr" in calls
        assert result["engine"].startswith("easyocr:")

    def test_customer_recognition_prompt_includes_ocr_candidates(self):
        from app.services.ai.prompts.customer_prompts import (
            customer_recognition_from_ocr_candidates_prompt,
        )

        prompt = customer_recognition_from_ocr_candidates_prompt(
            "深圳市星河电子有限公司\n张工",
            [
                {
                    "engine": "rapidocr:original",
                    "confidence": 0.9,
                    "score": 3.1,
                    "key_hits": ["phone", "email"],
                    "text": "张工 13800001111 zhang@example.com",
                },
                {
                    "engine": "rapidocr:threshold_190",
                    "confidence": 0.8,
                    "score": 2.4,
                    "key_hits": ["address"],
                    "text": "地址: 深圳市南山区科技园",
                },
            ],
        )

        assert "OCR 多候选文本" in prompt
        assert "rapidocr:original" in prompt
        assert "13800001111" in prompt
        assert "深圳市南山区科技园" in prompt

    async def test_customer_recognition_fallback_uses_ocr_candidates(self, monkeypatch):
        from app.services.ai.agents import CustomerAgent

        async def fake_chat_structured(*_args, **_kwargs):
            raise RuntimeError("AI down")

        monkeypatch.setattr(
            "app.services.ai.client.ai_client.chat_structured",
            fake_chat_structured,
        )

        result = await CustomerAgent.recognize_customer(
            "深圳市星河电子有限公司\n张工 13800001111",
            ocr_candidates=[
                {"text": "zhang@example.com"},
                {"text": "地址: 深圳市南山区科技园"},
            ],
        )

        assert result["name"] == "深圳市星河电子有限公司"
        assert result["phone"] == "13800001111"
        assert result["email"] == "zhang@example.com"
        assert result["address"] == "深圳市南山区科技园"

    async def test_customer_recognition_ai_result_is_completed_from_ocr_candidates(
        self, monkeypatch
    ):
        from app.services.ai.agents import CustomerAgent

        async def fake_chat_structured(*_args, **_kwargs):
            return {
                "name": "深圳市星河电子有限公司",
                "short_name": "星河电子",
                "customer_type": "",
                "industry": "",
                "level": "",
                "region": "",
                "source": "",
                "contact_person": "张工",
                "phone": "",
                "email": "",
                "owner": "",
                "credit_limit": None,
                "credit_level": "",
                "address": "",
                "notes": "",
                "confidence": 0.8,
                "summary": "AI识别部分字段",
            }

        monkeypatch.setattr(
            "app.services.ai.client.ai_client.chat_structured",
            fake_chat_structured,
        )

        result = await CustomerAgent.recognize_customer(
            "深圳市星河电子有限公司\n张工",
            ocr_candidates=[
                {"text": "电话: 13800001111"},
                {"text": "Email: zhang@example.com"},
                {"text": "地址: 深圳市南山区科技园"},
            ],
        )

        assert result["phone"] == "13800001111"
        assert result["email"] == "zhang@example.com"
        assert result["address"] == "深圳市南山区科技园"
        assert result["confidence"] == 0.8

    async def test_ai_recognize_customer_fallback_extracts_key_fields(
        self, async_client: AsyncClient, auth_headers: dict, monkeypatch
    ):
        async def fake_chat_structured(*_args, **_kwargs):
            raise RuntimeError("AI down")

        monkeypatch.setattr(
            "app.services.ai.client.ai_client.chat_structured",
            fake_chat_structured,
        )

        text = (
            "公司：深圳市星河电子有限公司，联系人：张工，手机：13800001111，"
            "邮箱：zhang@example.com，行业：车规电子，区域：深圳，来源：expo，"
            "负责人：王明，授信：20万，类型：OEM。"
        )
        resp = await async_client.post(
            "/api/v1/ai/customer/recognition",
            headers=auth_headers,
            json={"text": text},
        )

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["name"] == "深圳市星河电子有限公司"
        assert data["short_name"] in ("星河电子", "深圳市星河电子")
        assert data["phone"] == "13800001111"
        assert data["email"] == "zhang@example.com"
        assert data["industry"] == "汽车电子"
        assert data["region"] == "华南"
        assert data["source"] == "展会"
        assert data["customer_type"] == "OEM"
        assert data["owner"] == "王明"
        assert data["credit_limit"] == 200000

    async def test_ai_recognize_customer_fallback_complex_text(
        self, async_client: AsyncClient, auth_headers: dict, monkeypatch
    ):
        async def fake_chat_structured(*_args, **_kwargs):
            raise RuntimeError("AI down")

        monkeypatch.setattr(
            "app.services.ai.client.ai_client.chat_structured",
            fake_chat_structured,
        )

        text = (
            "Company: Shenzhen Nova Tech Co., Ltd. contact: Alice 电话:0755-12345678 手机:13912345678 "
            "email:alice@novatech.com 行业: automotive electronics 区域: 广东 来源: website留资 "
            "授信等级:A 授信:80万 owner:Bob"
        )
        resp = await async_client.post(
            "/api/v1/ai/customer/recognition",
            headers=auth_headers,
            json={"text": text},
        )

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["phone"] == "13912345678"
        assert data["email"] == "alice@novatech.com"
        assert data["industry"] == "汽车电子"
        assert data["region"] == "华南"
        assert data["source"] == "线上推广"
        assert data["credit_level"] == "A"
        assert data["credit_limit"] == 800000

    async def test_ai_recognize_customer_fallback_repairs_ocr_spacing(
        self, async_client: AsyncClient, auth_headers: dict, monkeypatch
    ):
        async def fake_chat_structured(*_args, **_kwargs):
            raise RuntimeError("AI down")

        monkeypatch.setattr(
            "app.services.ai.client.ai_client.chat_structured",
            fake_chat_structured,
        )

        text = (
            "深圳市星河电子有限公司\n"
            "张伟 / 销售经理\n"
            "Mobile: 138-0000 1111\n"
            "E mail: zhang @ example . com\n"
            "Address: 深圳市南山区科技园"
        )
        resp = await async_client.post(
            "/api/v1/ai/customer/recognition",
            headers=auth_headers,
            json={"text": text},
        )

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["name"] == "深圳市星河电子有限公司"
        assert data["contact_person"] == "张伟"
        assert data["phone"] == "13800001111"
        assert data["email"] == "zhang@example.com"
        assert data["address"] == "深圳市南山区科技园"

    def test_customer_fallback_helpers_extract_name_and_title_line(self):
        from app.services.ai.agents import _heuristic_customer_recognition

        result = _heuristic_customer_recognition(
            "Shenzhen Nova Electronics Co., Ltd.\nAlice Wang Sales Director\nTel: 0755-1234 5678\nEmail: alice @ nova . com"
        )

        assert result["name"] == "Shenzhen Nova Electronics Co."
        assert result["contact_person"] == "Alice Wang"
        assert result["phone"] == "075512345678"
        assert result["email"] == "alice@nova.com"


class TestCustomerContacts:
    """Contact management."""

    async def test_add_contact(self, async_client: AsyncClient, auth_headers: dict):
        cust = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "联系人测试客户", "type": "终端客户"},
        )
        cid = cust.json()["data"]["id"]
        resp = await async_client.post(
            f"/api/v1/customers/{cid}/contacts",
            headers=auth_headers,
            json={"name": "张三", "phone": "13800001111"},
        )
        assert resp.status_code == 201
        assert resp.json()["code"] == 0

    async def test_list_contacts(self, async_client: AsyncClient, auth_headers: dict):
        cust = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "列表联系人", "type": "终端客户"},
        )
        cid = cust.json()["data"]["id"]
        resp = await async_client.get(
            f"/api/v1/customers/{cid}/contacts", headers=auth_headers
        )
        assert resp.status_code == 200
        assert isinstance(resp.json()["data"], list)

    async def test_delete_contact(self, async_client: AsyncClient, auth_headers: dict):
        cust = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "删除联系人", "type": "终端客户"},
        )
        cid = cust.json()["data"]["id"]
        contact = await async_client.post(
            f"/api/v1/customers/{cid}/contacts",
            headers=auth_headers,
            json={"name": "李四", "phone": "13800001112"},
        )
        contact_id = contact.json()["data"]["id"]
        resp = await async_client.delete(
            f"/api/v1/customers/{cid}/contacts/{contact_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200


class TestCustomerFollowups:
    """Follow-up records."""

    async def test_add_followup(self, async_client: AsyncClient, auth_headers: dict):
        cust = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "跟进测试", "type": "终端客户"},
        )
        cid = cust.json()["data"]["id"]
        resp = await async_client.post(
            f"/api/v1/customers/{cid}/follow-ups",
            headers=auth_headers,
            json={"content": "初次拜访", "type": "拜访"},
        )
        assert resp.status_code == 201
        assert resp.json()["code"] == 0

    async def test_list_followups(self, async_client: AsyncClient, auth_headers: dict):
        cust = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "列表跟进", "type": "终端客户"},
        )
        cid = cust.json()["data"]["id"]
        resp = await async_client.get(
            f"/api/v1/customers/{cid}/follow-ups", headers=auth_headers
        )
        assert resp.status_code == 200
        assert isinstance(resp.json()["data"], list)

    async def test_update_followup(self, async_client: AsyncClient, auth_headers: dict):
        cust = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "更新跟进", "type": "终端客户"},
        )
        cid = cust.json()["data"]["id"]
        fup = await async_client.post(
            f"/api/v1/customers/{cid}/follow-ups",
            headers=auth_headers,
            json={"content": "原始内容", "type": "拜访"},
        )
        fup_id = fup.json()["data"]["id"]
        resp = await async_client.put(
            f"/api/v1/customers/{cid}/follow-ups/{fup_id}",
            headers=auth_headers,
            json={"content": "已更新内容"},
        )
        assert resp.status_code == 200

    async def test_update_followup_planned_time(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        cust = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "改期跟进", "type": "终端客户"},
        )
        cid = cust.json()["data"]["id"]
        fup = await async_client.post(
            f"/api/v1/customers/{cid}/follow-ups",
            headers=auth_headers,
            json={
                "content": "确认样品进度",
                "status": "planned",
                "planned_at": "2026-05-25 09:00:00",
            },
        )
        fup_id = fup.json()["data"]["id"]

        resp = await async_client.put(
            f"/api/v1/customers/{cid}/follow-ups/{fup_id}",
            headers=auth_headers,
            json={"status": "planned", "planned_at": "2026-05-27 15:30:00"},
        )
        assert resp.status_code == 200

        listed = await async_client.get(
            f"/api/v1/customers/{cid}/follow-ups", headers=auth_headers
        )
        updated = next(item for item in listed.json()["data"] if item["id"] == fup_id)
        assert updated["planned_at"].startswith("2026-05-27 15:30:00")

    async def test_ai_recognize_followup(
        self, async_client: AsyncClient, auth_headers: dict, monkeypatch
    ):
        cust = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "AI识别跟进客户", "type": "终端客户"},
        )
        cid = cust.json()["data"]["id"]

        async def fake_recognize_followup(
            text: str, customer_data: dict, now_text: str
        ):
            assert "明天下午3点" in text
            assert customer_data["name"] == "AI识别跟进客户"
            assert now_text
            return {
                "method": "phone",
                "status": "planned",
                "priority": "high",
                "content": "客户需要重新评估BOM价格",
                "result": "",
                "planned_at": "2026-05-20 15:00:00",
                "completed_at": "",
                "assigned_to": "王明",
                "confidence": 0.86,
                "summary": "识别为高优先级电话跟进计划",
            }

        monkeypatch.setattr(
            "app.api.v1.ai.customer.recognition.CustomerAgent.recognize_followup",
            fake_recognize_followup,
        )

        resp = await async_client.post(
            f"/api/v1/ai/customer/{cid}/followup-recognition",
            headers=auth_headers,
            json={
                "text": "今天和客户电话沟通，明天下午3点再电话确认BOM价格，优先级高，负责人王明。"
            },
        )

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["method"] == "phone"
        assert data["status"] == "planned"
        assert data["priority"] == "high"
        assert data["planned_at"] == "2026-05-20 15:00:00"
        assert data["assigned_to"] == "王明"
        assert data["confidence"] == 0.86


class TestCustomerStats:
    """Customer analytics endpoints."""

    async def test_customer_stats(self, async_client: AsyncClient, auth_headers: dict):
        cust = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "统计客户", "type": "终端客户"},
        )
        cid = cust.json()["data"]["id"]
        resp = await async_client.get(
            f"/api/v1/customers/{cid}/stats", headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_customer_timeline(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        cust = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "时间线客户", "type": "终端客户"},
        )
        cid = cust.json()["data"]["id"]
        resp = await async_client.get(
            f"/api/v1/customers/{cid}/timeline", headers=auth_headers
        )
        assert resp.status_code == 200
        assert isinstance(resp.json()["data"], list)

    async def test_overdue_followups(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        resp = await async_client.get(
            "/api/v1/customers/overdue-followups", headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_overdue_followups_only_include_scheduled_open_items(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        cust = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "跟进提醒客户", "type": "终端客户"},
        )
        cid = cust.json()["data"]["id"]

        unscheduled = await async_client.post(
            f"/api/v1/customers/{cid}/follow-ups",
            headers=auth_headers,
            json={"method": "phone", "status": "planned", "content": "无计划时间"},
        )
        assert unscheduled.status_code == 201

        past_time = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
        scheduled = await async_client.post(
            f"/api/v1/customers/{cid}/follow-ups",
            headers=auth_headers,
            json={"method": "phone", "status": "planned", "planned_at": past_time},
        )
        scheduled_id = scheduled.json()["data"]["id"]

        overdue = await async_client.get(
            "/api/v1/customers/overdue-followups", headers=auth_headers
        )
        overdue_ids = {item["id"] for item in overdue.json()["data"]["items"]}
        assert scheduled_id in overdue_ids
        assert unscheduled.json()["data"]["id"] not in overdue_ids

        await async_client.put(
            f"/api/v1/customers/{cid}/follow-ups/{scheduled_id}",
            headers=auth_headers,
            json={"status": "completed"},
        )
        overdue_after_complete = await async_client.get(
            "/api/v1/customers/overdue-followups", headers=auth_headers
        )
        overdue_ids_after_complete = {
            item["id"] for item in overdue_after_complete.json()["data"]["items"]
        }
        assert scheduled_id not in overdue_ids_after_complete

    async def test_follow_up_reminders_group_by_due_bucket(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        cust = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "提醒分组客户", "type": "终端客户"},
        )
        cid = cust.json()["data"]["id"]
        now = datetime.now(timezone.utc)

        past = await async_client.post(
            f"/api/v1/customers/{cid}/follow-ups",
            headers=auth_headers,
            json={
                "method": "phone",
                "status": "planned",
                "planned_at": (now - timedelta(days=2)).isoformat(),
            },
        )
        today = await async_client.post(
            f"/api/v1/customers/{cid}/follow-ups",
            headers=auth_headers,
            json={
                "method": "email",
                "status": "planned",
                "planned_at": now.isoformat(),
            },
        )
        upcoming = await async_client.post(
            f"/api/v1/customers/{cid}/follow-ups",
            headers=auth_headers,
            json={
                "method": "visit",
                "status": "planned",
                "planned_at": (now + timedelta(days=3)).isoformat(),
            },
        )

        resp = await async_client.get(
            "/api/v1/customers/follow-up-reminders", headers=auth_headers
        )
        assert resp.status_code == 200
        items_by_id = {item["id"]: item for item in resp.json()["data"]["items"]}
        assert items_by_id[past.json()["data"]["id"]]["due_bucket"] == "overdue"
        assert items_by_id[today.json()["data"]["id"]]["due_bucket"] == "today"
        assert items_by_id[upcoming.json()["data"]["id"]]["due_bucket"] == "upcoming"

    async def test_global_follow_ups_collection(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        target = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "全局跟进客户", "type": "终端客户"},
        )
        other = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "其他全局客户", "type": "终端客户"},
        )
        target_id = target.json()["data"]["id"]
        other_id = other.json()["data"]["id"]
        now = datetime.now(timezone.utc)

        target_follow = await async_client.post(
            f"/api/v1/customers/{target_id}/follow-ups",
            headers=auth_headers,
            json={
                "method": "phone",
                "status": "planned",
                "priority": "high",
                "planned_at": (now - timedelta(days=1)).isoformat(),
                "content": "全局集合关键字",
            },
        )
        await async_client.post(
            f"/api/v1/customers/{other_id}/follow-ups",
            headers=auth_headers,
            json={"method": "email", "status": "completed", "content": "其他记录"},
        )

        resp = await async_client.get(
            "/api/v1/customers/follow-ups-global?q=全局集合关键字&due_bucket=overdue",
            headers=auth_headers,
        )

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 1
        item = data["list"][0]
        assert item["id"] == target_follow.json()["data"]["id"]
        assert item["customer_id"] == target_id
        assert item["customer_name"] == "全局跟进客户"
        assert item["due_bucket"] == "overdue"
        assert item["priority"] == "high"

    async def test_customer_alerts(self, async_client: AsyncClient, auth_headers: dict):
        resp = await async_client.get("/api/v1/customers/alerts", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_alert_rules_crud(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        # create
        create = await async_client.post(
            "/api/v1/customers/alerts/rules",
            headers=auth_headers,
            json={"name": "逾期规则", "rule_type": "ar_overdue", "threshold_days": 30},
        )
        assert create.status_code == 201
        rule_id = create.json()["data"]["id"]
        # update
        upd = await async_client.put(
            f"/api/v1/customers/alerts/rules/{rule_id}",
            headers=auth_headers,
            json={"threshold_days": 15},
        )
        assert upd.status_code == 200
        # delete
        del_ = await async_client.delete(
            f"/api/v1/customers/alerts/rules/{rule_id}",
            headers=auth_headers,
        )
        assert del_.status_code == 200


class TestCustomerLevelRules:
    """Customer level (A/B/C) management."""

    async def test_level_rules_crud(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        # create rule
        create = await async_client.post(
            "/api/v1/customers/level-rules",
            headers=auth_headers,
            json={
                "name": "A类客户规则",
                "target_level": "A",
                "condition_type": "revenue",
                "operator": ">=",
                "threshold_value": 100000,
                "period_days": 365,
            },
        )
        assert create.status_code == 201
        rule_id = create.json()["data"]["id"]
        # update
        upd = await async_client.put(
            f"/api/v1/customers/level-rules/{rule_id}",
            headers=auth_headers,
            json={"threshold_value": 50000},
        )
        assert upd.status_code == 200
        # delete
        del_ = await async_client.delete(
            f"/api/v1/customers/level-rules/{rule_id}",
            headers=auth_headers,
        )
        assert del_.status_code == 200

    async def test_list_level_rules(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        resp = await async_client.get(
            "/api/v1/customers/level-rules", headers=auth_headers
        )
        assert resp.status_code == 200
        assert isinstance(resp.json()["data"], list)


class TestCustomerTags:
    async def test_generate_default_customer_tags_is_idempotent(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        first = await async_client.post(
            "/api/v1/customers/tags/defaults", headers=auth_headers
        )
        assert first.status_code == 201
        first_data = first.json()["data"]
        assert first_data["created"] == 5
        assert [tag["name"] for tag in first_data["tags"]] == [
            "重点客户",
            "潜在客户",
            "样品跟进",
            "价格敏感",
            "风险预警",
        ]

        second = await async_client.post(
            "/api/v1/customers/tags/defaults", headers=auth_headers
        )
        assert second.status_code == 201
        second_data = second.json()["data"]
        assert second_data["created"] == 0
        assert second_data["existing"] == 5

        listed = await async_client.get("/api/v1/customers/tags", headers=auth_headers)
        assert listed.status_code == 200
        assert {tag["name"] for tag in listed.json()["data"]} == {
            "重点客户",
            "潜在客户",
            "样品跟进",
            "价格敏感",
            "风险预警",
        }
