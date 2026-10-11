from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone


class NotificationAdapter(ABC):
    """
    Abstract Base Class for candidate and institutional notifications.
    Decouples communication channels (SMS, Email, WhatsApp) from business logic.
    Real provider integrations belong to Phase 10.
    """

    @abstractmethod
    def send_activation_invite(
        self,
        recipient_email: str,
        recipient_mobile: str,
        student_name: str,
        raw_token: str,
        tnea_app_no: str
    ) -> Dict[str, Any]:
        """Dispatches an account activation notification with token."""
        pass

    @abstractmethod
    def dispatch_alert(
        self,
        channel: str,
        recipient_target: str,
        title: str,
        message: str,
        notification_type: str
    ) -> Dict[str, Any]:
        """Dispatches a mock communication channel alert."""
        pass


class MockNotificationAdapter(NotificationAdapter):
    """
    In-memory mock notification adapter for Phase 2, Phase 5, and Phase 8 simulation.
    Captures dispatched demo alerts for inspection without sending actual messages.
    """

    def __init__(self):
        self.sent_notifications: List[Dict[str, Any]] = []

    def send_activation_invite(
        self,
        recipient_email: str,
        recipient_mobile: str,
        student_name: str,
        raw_token: str,
        tnea_app_no: str
    ) -> Dict[str, Any]:
        payload = {
            "type": "ACCOUNT_ACTIVATION_AVAILABLE",
            "channel": "EMAIL_MOCK",
            "recipient_email": recipient_email,
            "recipient_mobile": recipient_mobile,
            "student_name": student_name,
            "tnea_application_number": tnea_app_no,
            "message": (
                f"Hello {student_name}, your allotment ({tnea_app_no}) at XYZ Engineering College "
                f"has been confirmed. Use your activation link/token to set up your AdmissionAI account."
            ),
            "raw_token": raw_token,
            "dispatched_at": datetime.now(timezone.utc).isoformat(),
            "status": "DELIVERED_MOCK"
        }
        self.sent_notifications.append(payload)
        return payload

    def dispatch_alert(
        self,
        channel: str,
        recipient_target: str,
        title: str,
        message: str,
        notification_type: str
    ) -> Dict[str, Any]:
        payload = {
            "type": notification_type,
            "channel": channel,
            "recipient_target": recipient_target,
            "title": title,
            "message": message,
            "dispatched_at": datetime.now(timezone.utc).isoformat(),
            "status": "DELIVERED_MOCK",
            "is_prototype": True
        }
        self.sent_notifications.append(payload)
        return payload

    def get_dispatched_notifications(self) -> List[Dict[str, Any]]:
        return list(self.sent_notifications)

    def clear(self) -> None:
        self.sent_notifications.clear()


# Global mock notification instance for simulation
mock_notification_service = MockNotificationAdapter()
