"""Credit Note (冲红发票) — RED phase (tests before implementation)."""

import pytest
from app.domain.shared.errors import InvalidStateTransition


# State machine tests
class TestCreditNoteStateMachine:
    """CreditNote: draft → issued | cancelled."""

    def _get_transitions(self):
        from app.domain.states.finance import CREDIT_NOTE_TRANSITIONS

        return CREDIT_NOTE_TRANSITIONS

    def _assert_can(self, current, target):
        from app.domain.states.finance import assert_can_transition_credit_note

        assert_can_transition_credit_note(current, target)

    def _assert_blocked(self, current, target):
        from app.domain.states.finance import assert_can_transition_credit_note

        with pytest.raises(InvalidStateTransition):
            assert_can_transition_credit_note(current, target)

    def test_draft_to_issued(self):
        self._assert_can("draft", "issued")

    def test_draft_to_cancelled(self):
        self._assert_can("draft", "cancelled")

    def test_issued_is_terminal(self):
        self._assert_blocked("issued", "draft")

    def test_cancelled_is_terminal(self):
        self._assert_blocked("cancelled", "draft")

    def test_draft_cannot_jump_to_unknown(self):
        self._assert_blocked("draft", "paid")

    def test_transitions_dict_structure(self):
        t = self._get_transitions()
        assert t["draft"] == {"issued", "cancelled"}
        assert t["issued"] == set()
        assert t["cancelled"] == set()


# Integration tests
class TestCreditNoteIntegration:
    """ReturnNote complete → CreditNote auto-generation."""

    async def _create_order(self, async_client, auth_headers, customer_id):
        r = await async_client.post(
            "/api/v1/sales-orders",
            headers=auth_headers,
            json={
                "customer_id": customer_id,
                "status": "pending",
                "total_amount": 50000,
                "items": [
                    {"product_name": "CN-Test", "quantity": 5, "unit_price": 10000}
                ],
            },
        )
        return r.json()["data"]["id"]

    async def _create_return(self, async_client, auth_headers, customer_id, order_id):
        # create delivery first
        r = await async_client.post(
            "/api/v1/delivery-notes",
            headers=auth_headers,
            json={
                "customer_id": customer_id,
                "sales_order_id": order_id,
                "status": "pending",
                "items": [{"product_name": "CN-Test", "quantity": 3}],
            },
        )
        note_id = r.json()["data"]["id"]
        await async_client.put(
            f"/api/v1/delivery-notes/{note_id}",
            headers=auth_headers,
            json={"status": "delivered"},
        )
        # create return
        r = await async_client.post(
            f"/api/v1/delivery-notes/{note_id}/convert-to-return?reason=质量问题",
            headers=auth_headers,
        )
        return r.json()["data"]["id"]

    async def test_complete_return_generates_credit_note(
        self, async_client, auth_headers, test_customer
    ):
        """Completing an approved return note auto-creates a credit note."""
        order_id = await self._create_order(
            async_client, auth_headers, test_customer["id"]
        )
        return_id = await self._create_return(
            async_client, auth_headers, test_customer["id"], order_id
        )
        # Return is created as "approved" — complete directly
        r = await async_client.post(
            f"/api/v1/return-notes/{return_id}/complete",
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["code"] == 0
        data = r.json()["data"]
        assert data["return_status"] == "completed"
        assert "credit_note_no" in data
        assert data["credit_note_amount"] < 0  # negative = credit

    async def test_complete_an_already_completed_return_fails(
        self, async_client, auth_headers, test_customer
    ):
        """Cannot complete a return that is already completed."""
        order_id = await self._create_order(
            async_client, auth_headers, test_customer["id"]
        )
        return_id = await self._create_return(
            async_client, auth_headers, test_customer["id"], order_id
        )
        # First complete
        await async_client.post(
            f"/api/v1/return-notes/{return_id}/complete",
            headers=auth_headers,
        )
        # Second complete should fail
        r = await async_client.post(
            f"/api/v1/return-notes/{return_id}/complete",
            headers=auth_headers,
        )
        assert r.json()["code"] == 409

    async def test_credit_note_negative_amount(
        self, async_client, auth_headers, test_customer
    ):
        """Credit note amount must equal negative of original invoice amount."""
        order_id = await self._create_order(
            async_client, auth_headers, test_customer["id"]
        )
        return_id = await self._create_return(
            async_client, auth_headers, test_customer["id"], order_id
        )
        await async_client.put(
            f"/api/v1/return-notes/{return_id}",
            headers=auth_headers,
            json={"status": "approved"},
        )
        r = await async_client.post(
            f"/api/v1/return-notes/{return_id}/complete",
            headers=auth_headers,
        )
        amount = r.json()["data"]["credit_note_amount"]
        assert amount == -50000.0  # negative of original order amount
