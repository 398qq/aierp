"""Sales return state machine — RED phase (tests before implementation)."""

import pytest
from app.domain.shared.errors import InvalidStateTransition

# Import will fail until we create the function — that's the RED signal
from app.domain.states.sales import (
    RETURN_TRANSITIONS,
    assert_can_transition_return,
)


class TestReturnNoteStateMachine:
    """ReturnNote: pending → approved → completed | rejected."""

    def test_pending_to_approved(self):
        assert_can_transition_return("pending", "approved")

    def test_pending_to_rejected(self):
        assert_can_transition_return("pending", "rejected")

    def test_approved_to_completed(self):
        assert_can_transition_return("approved", "completed")

    def test_approved_to_rejected(self):
        assert_can_transition_return("approved", "rejected")

    def test_completed_is_terminal(self):
        with pytest.raises(InvalidStateTransition):
            assert_can_transition_return("completed", "approved")
        with pytest.raises(InvalidStateTransition):
            assert_can_transition_return("completed", "pending")

    def test_rejected_is_terminal(self):
        with pytest.raises(InvalidStateTransition):
            assert_can_transition_return("rejected", "approved")

    def test_pending_cannot_jump_to_completed(self):
        with pytest.raises(InvalidStateTransition):
            assert_can_transition_return("pending", "completed")

    def test_unknown_blocked(self):
        with pytest.raises(InvalidStateTransition):
            assert_can_transition_return("bogus", "pending")


class TestReturnTransitions:
    """Verify RETURN_TRANSITIONS dict structure."""

    def test_pending_allows_approved_and_rejected(self):
        assert RETURN_TRANSITIONS["pending"] == {"approved", "rejected"}

    def test_approved_allows_completed_and_rejected(self):
        assert RETURN_TRANSITIONS["approved"] == {"completed", "rejected"}

    def test_completed_and_rejected_are_terminal(self):
        assert RETURN_TRANSITIONS["completed"] == set()
        assert RETURN_TRANSITIONS["rejected"] == set()
