from enum import Enum
from typing import Dict, List, Set, Tuple, Optional


class UserRole(str, Enum):
    STUDENT = "STUDENT"
    PARENT = "PARENT"
    ADMIN_VERIFIER = "ADMIN_VERIFIER"
    FINANCE_OFFICER = "FINANCE_OFFICER"
    ADMISSION_HEAD = "ADMISSION_HEAD"
    SUPER_ADMIN = "SUPER_ADMIN"
    SYSTEM = "SYSTEM"


class AdmissionState(str, Enum):
    # Initial / Ingestion & Activation
    ALLOTTED = "ALLOTTED"
    ACTIVATION_PENDING = "ACTIVATION_PENDING"
    ACTIVATED = "ACTIVATED"

    # Application & Documents
    APPLICATION_IN_PROGRESS = "APPLICATION_IN_PROGRESS"
    APPLICATION_SUBMITTED = "APPLICATION_SUBMITTED"
    DOCUMENT_PROCESSING = "DOCUMENT_PROCESSING"
    DOCUMENT_REVIEW = "DOCUMENT_REVIEW"
    CORRECTION_REQUIRED = "CORRECTION_REQUIRED"
    DOCUMENTS_VERIFIED = "DOCUMENTS_VERIFIED"

    # Campus Visit & Physical Verification
    VISIT_SCHEDULED = "VISIT_SCHEDULED"
    PHYSICAL_VERIFICATION = "PHYSICAL_VERIFICATION"

    # Payment & Finance
    PAYMENT_PENDING = "PAYMENT_PENDING"
    PAYMENT_SUBMITTED = "PAYMENT_SUBMITTED"
    PAYMENT_VERIFICATION = "PAYMENT_VERIFICATION"
    PAYMENT_VERIFIED = "PAYMENT_VERIFIED"

    # Institutional Enrollment & ERP
    ADMISSION_CONFIRMED = "ADMISSION_CONFIRMED"
    ERP_SYNC_PENDING = "ERP_SYNC_PENDING"
    ERP_SYNCED = "ERP_SYNCED"

    # Student Onboarding & Active
    ONBOARDING = "ONBOARDING"
    INDUCTION_READY = "INDUCTION_READY"
    ACTIVE_STUDENT = "ACTIVE_STUDENT"

    # Exception States
    WITHDRAWN = "WITHDRAWN"
    CANCELLED = "CANCELLED"
    ALLOTMENT_CHANGED = "ALLOTMENT_CHANGED"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    ERP_SYNC_FAILED = "ERP_SYNC_FAILED"


class StateTransitionError(Exception):
    """Base exception for state machine errors."""
    def __init__(self, message: str, current_state: str, requested_state: str):
        super().__init__(message)
        self.message = message
        self.current_state = current_state
        self.requested_state = requested_state


class InvalidStateTransitionError(StateTransitionError):
    """Raised when a state transition is not allowed by the lifecycle graph."""
    pass


class UnauthorizedTransitionError(StateTransitionError):
    """Raised when the actor's role is not authorized to trigger this transition."""
    pass


# Map of (CurrentState -> AllowedNextStates)
VALID_TRANSITIONS: Dict[AdmissionState, Set[AdmissionState]] = {
    AdmissionState.ALLOTTED: {
        AdmissionState.ACTIVATION_PENDING,
        AdmissionState.WITHDRAWN,
        AdmissionState.CANCELLED,
        AdmissionState.ALLOTMENT_CHANGED,
    },
    AdmissionState.ACTIVATION_PENDING: {
        AdmissionState.ACTIVATED,
        AdmissionState.WITHDRAWN,
        AdmissionState.CANCELLED,
    },
    AdmissionState.ACTIVATED: {
        AdmissionState.APPLICATION_IN_PROGRESS,
        AdmissionState.WITHDRAWN,
        AdmissionState.CANCELLED,
    },
    AdmissionState.APPLICATION_IN_PROGRESS: {
        AdmissionState.APPLICATION_SUBMITTED,
        AdmissionState.WITHDRAWN,
        AdmissionState.CANCELLED,
    },
    AdmissionState.APPLICATION_SUBMITTED: {
        AdmissionState.DOCUMENT_PROCESSING,
        AdmissionState.DOCUMENT_REVIEW,
        AdmissionState.DOCUMENTS_VERIFIED,
        AdmissionState.CORRECTION_REQUIRED,
        AdmissionState.WITHDRAWN,
        AdmissionState.CANCELLED,
    },
    AdmissionState.DOCUMENT_PROCESSING: {
        AdmissionState.DOCUMENT_REVIEW,
        AdmissionState.DOCUMENTS_VERIFIED,
        AdmissionState.CORRECTION_REQUIRED,
        AdmissionState.VERIFICATION_FAILED,
    },
    AdmissionState.DOCUMENT_REVIEW: {
        AdmissionState.DOCUMENTS_VERIFIED,
        AdmissionState.CORRECTION_REQUIRED,
        AdmissionState.VERIFICATION_FAILED,
        AdmissionState.WITHDRAWN,
    },
    AdmissionState.CORRECTION_REQUIRED: {
        AdmissionState.DOCUMENT_PROCESSING,
        AdmissionState.DOCUMENT_REVIEW,
        AdmissionState.WITHDRAWN,
        AdmissionState.CANCELLED,
    },
    AdmissionState.DOCUMENTS_VERIFIED: {
        AdmissionState.VISIT_SCHEDULED,
        AdmissionState.PHYSICAL_VERIFICATION,
        AdmissionState.PAYMENT_PENDING,
        AdmissionState.WITHDRAWN,
    },
    AdmissionState.VISIT_SCHEDULED: {
        AdmissionState.PHYSICAL_VERIFICATION,
        AdmissionState.WITHDRAWN,
        AdmissionState.CANCELLED,
    },
    AdmissionState.PHYSICAL_VERIFICATION: {
        AdmissionState.PAYMENT_PENDING,
        AdmissionState.VERIFICATION_FAILED,
        AdmissionState.WITHDRAWN,
    },
    AdmissionState.PAYMENT_PENDING: {
        AdmissionState.PAYMENT_SUBMITTED,
        AdmissionState.WITHDRAWN,
        AdmissionState.CANCELLED,
    },
    AdmissionState.PAYMENT_SUBMITTED: {
        AdmissionState.PAYMENT_VERIFICATION,
        AdmissionState.PAYMENT_VERIFIED,
        AdmissionState.PAYMENT_FAILED,
    },
    AdmissionState.PAYMENT_VERIFICATION: {
        AdmissionState.PAYMENT_VERIFIED,
        AdmissionState.PAYMENT_FAILED,
    },
    AdmissionState.PAYMENT_VERIFIED: {
        AdmissionState.ADMISSION_CONFIRMED,
        AdmissionState.ERP_SYNC_PENDING,
    },
    AdmissionState.ADMISSION_CONFIRMED: {
        AdmissionState.ERP_SYNC_PENDING,
        AdmissionState.ERP_SYNCED,
        AdmissionState.ONBOARDING,
    },
    AdmissionState.ERP_SYNC_PENDING: {
        AdmissionState.ERP_SYNCED,
        AdmissionState.ERP_SYNC_FAILED,
    },
    AdmissionState.ERP_SYNC_FAILED: {
        AdmissionState.ERP_SYNC_PENDING,
        AdmissionState.ONBOARDING,
    },
    AdmissionState.ERP_SYNCED: {
        AdmissionState.ONBOARDING,
        AdmissionState.INDUCTION_READY,
    },
    AdmissionState.ONBOARDING: {
        AdmissionState.INDUCTION_READY,
        AdmissionState.ACTIVE_STUDENT,
    },
    AdmissionState.INDUCTION_READY: {
        AdmissionState.ACTIVE_STUDENT,
    },
    AdmissionState.ACTIVE_STUDENT: set(),
    AdmissionState.WITHDRAWN: set(),
    AdmissionState.CANCELLED: set(),
    AdmissionState.ALLOTMENT_CHANGED: {
        AdmissionState.ALLOTTED,
    },
    AdmissionState.VERIFICATION_FAILED: {
        AdmissionState.DOCUMENT_REVIEW,
        AdmissionState.WITHDRAWN,
        AdmissionState.CANCELLED,
    },
    AdmissionState.PAYMENT_FAILED: {
        AdmissionState.PAYMENT_PENDING,
        AdmissionState.WITHDRAWN,
    },
}

# Role permissions per target state transition
ROLE_TRANSITION_PERMISSIONS: Dict[AdmissionState, Set[UserRole]] = {
    AdmissionState.ALLOTTED: {UserRole.SUPER_ADMIN, UserRole.SYSTEM},
    AdmissionState.ACTIVATION_PENDING: {UserRole.STUDENT, UserRole.ADMIN_VERIFIER, UserRole.SUPER_ADMIN, UserRole.SYSTEM},
    AdmissionState.ACTIVATED: {UserRole.STUDENT, UserRole.SUPER_ADMIN, UserRole.SYSTEM},
    AdmissionState.APPLICATION_IN_PROGRESS: {UserRole.STUDENT, UserRole.SUPER_ADMIN},
    AdmissionState.APPLICATION_SUBMITTED: {UserRole.STUDENT, UserRole.SUPER_ADMIN},
    AdmissionState.DOCUMENT_PROCESSING: {UserRole.SYSTEM, UserRole.STUDENT, UserRole.SUPER_ADMIN},
    AdmissionState.DOCUMENT_REVIEW: {UserRole.ADMIN_VERIFIER, UserRole.ADMISSION_HEAD, UserRole.SUPER_ADMIN, UserRole.SYSTEM},
    AdmissionState.CORRECTION_REQUIRED: {UserRole.ADMIN_VERIFIER, UserRole.ADMISSION_HEAD, UserRole.SUPER_ADMIN, UserRole.SYSTEM},
    AdmissionState.DOCUMENTS_VERIFIED: {UserRole.ADMIN_VERIFIER, UserRole.ADMISSION_HEAD, UserRole.SUPER_ADMIN},
    AdmissionState.VISIT_SCHEDULED: {UserRole.STUDENT, UserRole.ADMIN_VERIFIER, UserRole.SUPER_ADMIN, UserRole.SYSTEM},
    AdmissionState.PHYSICAL_VERIFICATION: {UserRole.ADMIN_VERIFIER, UserRole.ADMISSION_HEAD, UserRole.SUPER_ADMIN},
    AdmissionState.PAYMENT_PENDING: {UserRole.ADMIN_VERIFIER, UserRole.FINANCE_OFFICER, UserRole.SUPER_ADMIN, UserRole.SYSTEM},
    AdmissionState.PAYMENT_SUBMITTED: {UserRole.STUDENT, UserRole.SUPER_ADMIN},
    AdmissionState.PAYMENT_VERIFICATION: {UserRole.FINANCE_OFFICER, UserRole.ADMISSION_HEAD, UserRole.SUPER_ADMIN},
    AdmissionState.PAYMENT_VERIFIED: {UserRole.FINANCE_OFFICER, UserRole.ADMISSION_HEAD, UserRole.SUPER_ADMIN},
    AdmissionState.ADMISSION_CONFIRMED: {UserRole.ADMISSION_HEAD, UserRole.SUPER_ADMIN, UserRole.SYSTEM},
    AdmissionState.ERP_SYNC_PENDING: {UserRole.ADMISSION_HEAD, UserRole.SUPER_ADMIN, UserRole.SYSTEM},
    AdmissionState.ERP_SYNCED: {UserRole.SUPER_ADMIN, UserRole.SYSTEM},
    AdmissionState.ERP_SYNC_FAILED: {UserRole.SUPER_ADMIN, UserRole.SYSTEM},
    AdmissionState.ONBOARDING: {UserRole.STUDENT, UserRole.ADMISSION_HEAD, UserRole.SUPER_ADMIN, UserRole.SYSTEM},
    AdmissionState.INDUCTION_READY: {UserRole.ADMISSION_HEAD, UserRole.SUPER_ADMIN, UserRole.SYSTEM},
    AdmissionState.ACTIVE_STUDENT: {UserRole.ADMISSION_HEAD, UserRole.SUPER_ADMIN, UserRole.SYSTEM},
    AdmissionState.WITHDRAWN: {UserRole.STUDENT, UserRole.ADMISSION_HEAD, UserRole.SUPER_ADMIN},
    AdmissionState.CANCELLED: {UserRole.ADMISSION_HEAD, UserRole.SUPER_ADMIN},
    AdmissionState.ALLOTMENT_CHANGED: {UserRole.ADMISSION_HEAD, UserRole.SUPER_ADMIN, UserRole.SYSTEM},
    AdmissionState.VERIFICATION_FAILED: {UserRole.ADMIN_VERIFIER, UserRole.ADMISSION_HEAD, UserRole.SUPER_ADMIN},
    AdmissionState.PAYMENT_FAILED: {UserRole.FINANCE_OFFICER, UserRole.ADMISSION_HEAD, UserRole.SUPER_ADMIN},
}


def can_transition(
    current_state: AdmissionState,
    requested_state: AdmissionState,
    actor_role: UserRole
) -> Tuple[bool, Optional[str]]:
    """
    Checks if a transition from current_state to requested_state is valid
    and if the actor_role has sufficient authority.
    Returns: (is_allowed, error_reason)
    """
    if current_state == requested_state:
        return False, f"Current state is already {current_state.value}"

    allowed_next_states = VALID_TRANSITIONS.get(current_state, set())
    if requested_state not in allowed_next_states:
        return False, f"Transition from {current_state.value} to {requested_state.value} is invalid"

    allowed_roles = ROLE_TRANSITION_PERMISSIONS.get(requested_state, set())
    if actor_role not in allowed_roles and actor_role != UserRole.SUPER_ADMIN:
        return False, f"Role {actor_role.value} is not authorized to transition state to {requested_state.value}"

    return True, None


def validate_and_transition(
    current_state: AdmissionState,
    requested_state: AdmissionState,
    actor_role: UserRole
) -> AdmissionState:
    """
    Validates a transition. If valid, returns the new state.
    Otherwise raises InvalidStateTransitionError or UnauthorizedTransitionError.
    """
    if current_state == requested_state:
        return current_state

    allowed_next_states = VALID_TRANSITIONS.get(current_state, set())
    if requested_state not in allowed_next_states:
        raise InvalidStateTransitionError(
            f"Invalid transition from '{current_state.value}' to '{requested_state.value}'",
            current_state=current_state.value,
            requested_state=requested_state.value
        )

    allowed_roles = ROLE_TRANSITION_PERMISSIONS.get(requested_state, set())
    if actor_role not in allowed_roles and actor_role != UserRole.SUPER_ADMIN:
        raise UnauthorizedTransitionError(
            f"Role '{actor_role.value}' is not permitted to trigger transition to '{requested_state.value}'",
            current_state=current_state.value,
            requested_state=requested_state.value
        )

    return requested_state
