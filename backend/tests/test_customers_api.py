"""Customer API tests."""
from datetime import datetime, timedelta, timezone

from httpx import AsyncClient


class TestCustomers:
    """Customer CRUD + batch operations."""

    async def test_list_empty(self, async_client: AsyncClient, auth_headers: dict):
        resp = await async_client.get("/api/v1/customers", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

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
        detail = await async_client.get(f"/api/v1/customers/{cid}", headers=auth_headers)
        assert detail.json()["data"]["created_at"]

        customers = await async_client.get("/api/v1/customers", headers=auth_headers)
        row = next(item for item in customers.json()["data"]["list"] if item["id"] == cid)
        assert row["created_at"]

    async def test_create_customer_auto_generates_short_name(self, async_client: AsyncClient, auth_headers: dict):
        resp = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "深圳市星河电子有限公司", "type": "终端客户"},
        )
        assert resp.status_code == 201
        cid = resp.json()["data"]["id"]

        detail = await async_client.get(f"/api/v1/customers/{cid}", headers=auth_headers)
        assert detail.status_code == 200
        assert detail.json()["data"]["short_name"] == "深圳市星河电子"

    async def test_create_customer_keeps_manual_short_name(self, async_client: AsyncClient, auth_headers: dict):
        resp = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "上海星河电子有限公司", "short_name": "星河", "type": "终端客户"},
        )
        assert resp.status_code == 201
        cid = resp.json()["data"]["id"]

        detail = await async_client.get(f"/api/v1/customers/{cid}", headers=auth_headers)
        assert detail.status_code == 200
        assert detail.json()["data"]["short_name"] == "星河"

    async def test_create_customer_dedupes_auto_short_name_conflicts(self, async_client: AsyncClient, auth_headers: dict):
        first = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "冲突简称电子有限公司", "type": "终端客户"},
        )
        second = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "冲突简称电子有限公司", "type": "终端客户"},
        )
        assert first.status_code == 201
        assert second.status_code == 201

        first_detail = await async_client.get(f"/api/v1/customers/{first.json()['data']['id']}", headers=auth_headers)
        second_detail = await async_client.get(f"/api/v1/customers/{second.json()['data']['id']}", headers=auth_headers)
        first_short_name = first_detail.json()["data"]["short_name"]
        second_short_name = second_detail.json()["data"]["short_name"]

        assert first_short_name == "冲突简称电子"
        assert second_short_name.startswith("冲突简称电子-")
        assert second_short_name != first_short_name

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

    async def test_delete_customer(self, async_client: AsyncClient, auth_headers: dict):
        c = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "待删除", "type": "终端客户"},
        )
        cid = c.json()["data"]["id"]
        resp = await async_client.delete(f"/api/v1/customers/{cid}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_batch_delete(self, async_client: AsyncClient, auth_headers: dict):
        c1 = await async_client.post(
            "/api/v1/customers", headers=auth_headers,
            json={"name": "批量删1", "type": "终端客户"},
        )
        c2 = await async_client.post(
            "/api/v1/customers", headers=auth_headers,
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

    async def test_unauthorized(self, async_client: AsyncClient):
        resp = await async_client.get("/api/v1/customers")
        assert resp.status_code == 401

    async def test_ai_recognize_customer(self, async_client: AsyncClient, auth_headers: dict, monkeypatch):
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
            "app.api.v1.ai.customer_ai.CustomerAgent.recognize_customer",
            fake_recognize_customer,
        )

        resp = await async_client.post(
            "/api/v1/ai/customer/recognition",
            headers=auth_headers,
            json={"text": "深圳市星河电子有限公司，汽车电子OEM，联系人张工，13800001111，展会线索。"},
        )

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["name"] == "深圳市星河电子有限公司"
        assert data["customer_type"] == "OEM"
        assert data["industry"] == "汽车电子"
        assert data["region"] == "华南"
        assert data["credit_limit"] == 200000
        assert data["confidence"] == 0.9

    async def test_ai_recognize_business_card(self, async_client: AsyncClient, auth_headers: dict, monkeypatch):
        def fake_extract_business_card_ocr(content: bytes):
            assert content == b"fake-card-image"
            return {
                "text": "深圳市星河电子有限公司\n张工 13800001111\nzhang@example.com\n汽车电子OEM",
                "engine": "rapidocr",
                "confidence": 0.91,
                "score": 3.2,
                "candidates": [{"engine": "rapidocr", "confidence": 0.91, "score": 3.2, "text_length": 55}],
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
            "app.api.v1.ai.customer_ai._extract_business_card_ocr",
            fake_extract_business_card_ocr,
        )
        monkeypatch.setattr(
            "app.api.v1.ai.customer_ai.CustomerAgent.recognize_customer",
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
        assert data["recognition_warnings"] == []

    async def test_ai_recognize_business_card_accepts_body_file(self, async_client: AsyncClient, auth_headers: dict, monkeypatch):
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
            "app.api.v1.ai.customer_ai._extract_business_card_ocr",
            fake_extract_business_card_ocr,
        )
        monkeypatch.setattr(
            "app.api.v1.ai.customer_ai.CustomerAgent.recognize_customer",
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
                "candidates": [{"engine": "rapidocr:original", "confidence": 0.42, "score": 0.8, "text_length": 14}],
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
            "app.api.v1.ai.customer_ai._extract_business_card_ocr",
            fake_extract_business_card_ocr,
        )
        monkeypatch.setattr(
            "app.api.v1.ai.customer_ai.CustomerAgent.recognize_customer",
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
        assert "OCR评分较低，建议上传更清晰、无遮挡的名片图片" in data["recognition_warnings"]

    def test_business_card_ocr_scoring_prefers_field_rich_text(self):
        from app.api.v1.ai.customer_ai import _merge_card_ocr_results

        result = _merge_card_ocr_results([
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
        ])

        assert result["engine"] == "rapidocr:gray_autocontrast"
        assert result["text"].startswith("深圳市星河电子有限公司")
        assert result["score"] > 0
        assert len(result["candidates"]) == 2

    def test_business_card_ocr_merge_keeps_key_fields_from_other_candidates(self):
        from app.api.v1.ai.customer_ai import _merge_card_ocr_results

        result = _merge_card_ocr_results([
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
        ])

        assert result["engine"] == "rapidocr:original"
        assert "13800001111" in result["text"]
        assert "zhang@example.com" in result["text"]
        assert "深圳市南山区科技园" in result["text"]
        assert result["candidate_texts"][0]["engine"] == "rapidocr:original"
        assert "text" in result["candidate_texts"][0]

    def test_customer_recognition_prompt_includes_ocr_candidates(self):
        from app.services.ai.prompts.customer_prompts import customer_recognition_from_ocr_candidates_prompt

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
            "app.services.ai.agents.ai_client.chat_structured",
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

    async def test_customer_recognition_ai_result_is_completed_from_ocr_candidates(self, monkeypatch):
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
            "app.services.ai.agents.ai_client.chat_structured",
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

    async def test_ai_recognize_customer_fallback_extracts_key_fields(self, async_client: AsyncClient, auth_headers: dict, monkeypatch):
        async def fake_chat_structured(*_args, **_kwargs):
            raise RuntimeError("AI down")

        monkeypatch.setattr(
            "app.services.ai.agents.ai_client.chat_structured",
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

    async def test_ai_recognize_customer_fallback_complex_text(self, async_client: AsyncClient, auth_headers: dict, monkeypatch):
        async def fake_chat_structured(*_args, **_kwargs):
            raise RuntimeError("AI down")

        monkeypatch.setattr(
            "app.services.ai.agents.ai_client.chat_structured",
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

    async def test_ai_recognize_customer_fallback_repairs_ocr_spacing(self, async_client: AsyncClient, auth_headers: dict, monkeypatch):
        async def fake_chat_structured(*_args, **_kwargs):
            raise RuntimeError("AI down")

        monkeypatch.setattr(
            "app.services.ai.agents.ai_client.chat_structured",
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
        resp = await async_client.get(f"/api/v1/customers/{cid}/contacts", headers=auth_headers)
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
        resp = await async_client.get(f"/api/v1/customers/{cid}/follow-ups", headers=auth_headers)
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

    async def test_ai_recognize_followup(self, async_client: AsyncClient, auth_headers: dict, monkeypatch):
        cust = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "AI识别跟进客户", "type": "终端客户"},
        )
        cid = cust.json()["data"]["id"]

        async def fake_recognize_followup(text: str, customer_data: dict, now_text: str):
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
            "app.api.v1.ai.customer_ai.CustomerAgent.recognize_followup",
            fake_recognize_followup,
        )

        resp = await async_client.post(
            f"/api/v1/ai/customer/{cid}/followup-recognition",
            headers=auth_headers,
            json={"text": "今天和客户电话沟通，明天下午3点再电话确认BOM价格，优先级高，负责人王明。"},
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
        resp = await async_client.get(f"/api/v1/customers/{cid}/stats", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_customer_timeline(self, async_client: AsyncClient, auth_headers: dict):
        cust = await async_client.post(
            "/api/v1/customers",
            headers=auth_headers,
            json={"name": "时间线客户", "type": "终端客户"},
        )
        cid = cust.json()["data"]["id"]
        resp = await async_client.get(f"/api/v1/customers/{cid}/timeline", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json()["data"], list)

    async def test_overdue_followups(self, async_client: AsyncClient, auth_headers: dict):
        resp = await async_client.get("/api/v1/customers/overdue-followups", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_overdue_followups_only_include_scheduled_open_items(self, async_client: AsyncClient, auth_headers: dict):
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

        overdue = await async_client.get("/api/v1/customers/overdue-followups", headers=auth_headers)
        overdue_ids = {item["id"] for item in overdue.json()["data"]["items"]}
        assert scheduled_id in overdue_ids
        assert unscheduled.json()["data"]["id"] not in overdue_ids

        await async_client.put(
            f"/api/v1/customers/{cid}/follow-ups/{scheduled_id}",
            headers=auth_headers,
            json={"status": "completed"},
        )
        overdue_after_complete = await async_client.get("/api/v1/customers/overdue-followups", headers=auth_headers)
        overdue_ids_after_complete = {item["id"] for item in overdue_after_complete.json()["data"]["items"]}
        assert scheduled_id not in overdue_ids_after_complete

    async def test_follow_up_reminders_group_by_due_bucket(self, async_client: AsyncClient, auth_headers: dict):
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
            json={"method": "phone", "status": "planned", "planned_at": (now - timedelta(days=2)).isoformat()},
        )
        today = await async_client.post(
            f"/api/v1/customers/{cid}/follow-ups",
            headers=auth_headers,
            json={"method": "email", "status": "planned", "planned_at": now.isoformat()},
        )
        upcoming = await async_client.post(
            f"/api/v1/customers/{cid}/follow-ups",
            headers=auth_headers,
            json={"method": "visit", "status": "planned", "planned_at": (now + timedelta(days=3)).isoformat()},
        )

        resp = await async_client.get("/api/v1/customers/follow-up-reminders", headers=auth_headers)
        assert resp.status_code == 200
        items_by_id = {item["id"]: item for item in resp.json()["data"]["items"]}
        assert items_by_id[past.json()["data"]["id"]]["due_bucket"] == "overdue"
        assert items_by_id[today.json()["data"]["id"]]["due_bucket"] == "today"
        assert items_by_id[upcoming.json()["data"]["id"]]["due_bucket"] == "upcoming"

    async def test_customer_alerts(self, async_client: AsyncClient, auth_headers: dict):
        resp = await async_client.get("/api/v1/customers/alerts", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    async def test_alert_rules_crud(self, async_client: AsyncClient, auth_headers: dict):
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

    async def test_level_rules_crud(self, async_client: AsyncClient, auth_headers: dict):
        # create rule
        create = await async_client.post(
            "/api/v1/customers/level-rules",
            headers=auth_headers,
            json={
                "name": "A类客户规则", "target_level": "A",
                "condition_type": "revenue", "operator": ">=",
                "threshold_value": 100000, "period_days": 365,
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

    async def test_list_level_rules(self, async_client: AsyncClient, auth_headers: dict):
        resp = await async_client.get("/api/v1/customers/level-rules", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json()["data"], list)
