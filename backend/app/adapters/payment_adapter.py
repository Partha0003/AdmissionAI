from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import uuid
from datetime import datetime, timezone


class PaymentAdapter(ABC):
    """
    Abstract Base Class for payment processing.
    Decouples payment simulation from business logic.
    Real payment gateway integrations belong to future production setups.
    """

    @abstractmethod
    def process_online_payment(
        self,
        payment_reference: str,
        amount: float,
        currency: str,
        student_name: str,
        simulate_failure: bool = False
    ) -> Dict[str, Any]:
        """Simulates processing of an online payment transaction."""
        pass


class MockPaymentAdapter(PaymentAdapter):
    """
    In-memory mock payment adapter for Phase 6 simulation.
    Clearly designated as PROTOTYPE SIMULATION ONLY.
    """

    def process_online_payment(
        self,
        payment_reference: str,
        amount: float,
        currency: str,
        student_name: str,
        simulate_failure: bool = False
    ) -> Dict[str, Any]:
        now_str = datetime.now(timezone.utc).isoformat()
        if simulate_failure:
            return {
                "success": False,
                "status": "FAILED",
                "transaction_id": f"MOCK-TXN-FAIL-{uuid.uuid4().hex[:8].upper()}",
                "payment_reference": payment_reference,
                "amount": amount,
                "currency": currency,
                "error_message": "Prototype simulation: Transaction declined by mock bank sandbox.",
                "processed_at": now_str,
                "adapter": "MockPaymentAdapter",
                "is_prototype": True
            }

        return {
            "success": True,
            "status": "SUCCESS",
            "transaction_id": f"MOCK-TXN-SUCC-{uuid.uuid4().hex[:8].upper()}",
            "payment_reference": payment_reference,
            "amount": amount,
            "currency": currency,
            "gateway_reference": f"GW-XYZ-{uuid.uuid4().hex[:10].upper()}",
            "processed_at": now_str,
            "adapter": "MockPaymentAdapter",
            "is_prototype": True
        }


# Global instance
mock_payment_adapter = MockPaymentAdapter()
