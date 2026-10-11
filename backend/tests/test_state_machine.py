import pytest
from app.core.state_machine import (
    AdmissionState,
    UserRole,
    can_transition,
    validate_and_transition,
    InvalidStateTransitionError,
    UnauthorizedTransitionError,
)


def test_valid_state_transitions():
    # ALLOTTED -> ACTIVATION_PENDING (System / Admin)
    allowed, _ = can_transition(
        AdmissionState.ALLOTTED,
        AdmissionState.ACTIVATION_PENDING,
        UserRole.SYSTEM
    )
    assert allowed is True

    # ACTIVATION_PENDING -> ACTIVATED (Student)
    allowed, _ = can_transition(
        AdmissionState.ACTIVATION_PENDING,
        AdmissionState.ACTIVATED,
        UserRole.STUDENT
    )
    assert allowed is True

    # ACTIVATED -> APPLICATION_IN_PROGRESS (Student)
    new_state = validate_and_transition(
        AdmissionState.ACTIVATED,
        AdmissionState.APPLICATION_IN_PROGRESS,
        UserRole.STUDENT
    )
    assert new_state == AdmissionState.APPLICATION_IN_PROGRESS

    # APPLICATION_IN_PROGRESS -> APPLICATION_SUBMITTED (Student)
    new_state = validate_and_transition(
        AdmissionState.APPLICATION_IN_PROGRESS,
        AdmissionState.APPLICATION_SUBMITTED,
        UserRole.STUDENT
    )
    assert new_state == AdmissionState.APPLICATION_SUBMITTED


def test_invalid_state_transition_skipping():
    # Attempting to jump directly from ALLOTTED to PAYMENT_VERIFIED
    allowed, reason = can_transition(
        AdmissionState.ALLOTTED,
        AdmissionState.PAYMENT_VERIFIED,
        UserRole.STUDENT
    )
    assert allowed is False
    assert "invalid" in reason.lower()

    with pytest.raises(InvalidStateTransitionError):
        validate_and_transition(
            AdmissionState.ALLOTTED,
            AdmissionState.PAYMENT_VERIFIED,
            UserRole.STUDENT
        )


def test_unauthorized_state_transition_by_role():
    # Student cannot approve their own documents into DOCUMENTS_VERIFIED
    allowed, reason = can_transition(
        AdmissionState.DOCUMENT_REVIEW,
        AdmissionState.DOCUMENTS_VERIFIED,
        UserRole.STUDENT
    )
    assert allowed is False
    assert "not authorized" in reason.lower()

    with pytest.raises(UnauthorizedTransitionError):
        validate_and_transition(
            AdmissionState.DOCUMENT_REVIEW,
            AdmissionState.DOCUMENTS_VERIFIED,
            UserRole.STUDENT
        )

    # Admin Verifier is authorized
    allowed, _ = can_transition(
        AdmissionState.DOCUMENT_REVIEW,
        AdmissionState.DOCUMENTS_VERIFIED,
        UserRole.ADMIN_VERIFIER
    )
    assert allowed is True
