from httpx import AsyncClient


class TestContractBusinessRules:
    async def test_create_rejects_non_initial_status(
        self, async_client: AsyncClient, auth_headers: dict, test_customer: dict
    ):
        resp = await async_client.post(
            "/api/v1/contracts",
            headers=auth_headers,
            json={
                "customer_id": test_customer["id"],
                "title": "非法初始状态合同",
                "amount": 1000,
                "signed_date": "2026-06-01",
                "status": "active",
            },
        )

        assert resp.status_code == 422
        assert resp.json()["code"] == 422
        assert "body.status" in resp.json()["msg"]

    async def test_signed_contract_locks_amount(
        self, async_client: AsyncClient, auth_headers: dict, test_customer: dict
    ):
        created = await async_client.post(
            "/api/v1/contracts",
            headers=auth_headers,
            json={
                "customer_id": test_customer["id"],
                "title": "已签署合同",
                "amount": 1000,
                "signed_date": "2026-06-01",
                "status": "signed",
            },
        )
        assert created.status_code == 200, created.text
        contract_id = created.json()["data"]["id"]

        resp = await async_client.put(
            f"/api/v1/contracts/{contract_id}",
            headers=auth_headers,
            json={"amount": 2000},
        )

        assert resp.status_code == 422
        assert resp.json()["code"] == "BUSINESS_RULE_VIOLATION"
        assert "只能更新状态、文件和备注" in resp.json()["msg"]

    async def test_signed_contract_can_transition_to_active(
        self, async_client: AsyncClient, auth_headers: dict, test_customer: dict
    ):
        created = await async_client.post(
            "/api/v1/contracts",
            headers=auth_headers,
            json={
                "customer_id": test_customer["id"],
                "title": "状态流转合同",
                "amount": 1000,
                "signed_date": "2026-06-01",
                "status": "signed",
            },
        )
        assert created.status_code == 200, created.text
        contract_id = created.json()["data"]["id"]

        resp = await async_client.put(
            f"/api/v1/contracts/{contract_id}",
            headers=auth_headers,
            json={"status": "active"},
        )

        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["status"] == "active"

    async def test_delete_rejects_signed_contract(
        self, async_client: AsyncClient, auth_headers: dict, test_customer: dict
    ):
        created = await async_client.post(
            "/api/v1/contracts",
            headers=auth_headers,
            json={
                "customer_id": test_customer["id"],
                "title": "不可删除合同",
                "amount": 1000,
                "signed_date": "2026-06-01",
                "status": "signed",
            },
        )
        assert created.status_code == 200, created.text
        contract_id = created.json()["data"]["id"]

        resp = await async_client.delete(
            f"/api/v1/contracts/{contract_id}", headers=auth_headers
        )

        assert resp.status_code == 422
        assert "只能删除草稿合同" in resp.json()["msg"]

    async def test_import_contracts_rejects_invalid_status(
        self, async_client: AsyncClient, auth_headers: dict, test_customer: dict
    ):
        csv_data = (
            "title,customer_id,amount,status,signed_date,notes\n"
            f"导入非法合同,{test_customer['id']},50000,active,2026-06-01,测试"
        )
        resp = await async_client.post(
            "/api/v1/import/contracts",
            headers=auth_headers,
            files={"file": ("contracts.csv", csv_data.encode("utf-8-sig"), "text/csv")},
        )

        assert resp.status_code == 200
        payload = resp.json()["data"]
        assert payload["created"] == 0
        assert payload["errors"]
        assert "初始状态" in payload["errors"][0]
