from abc import ABC, abstractmethod
from typing import Dict, Any
import uuid
from datetime import datetime, timezone


class ERPAdapter(ABC):
    """
    Abstract Base Class for institutional ERP synchronization.
    Decouples ERP ingestion from admission domain logic.
    """

    @abstractmethod
    def sync_admission_record(
        self,
        staging_reference: str,
        payload: Dict[str, Any],
        simulate_failure: bool = False,
        failure_reason: str = None
    ) -> Dict[str, Any]:
        """Dispatches an ERP admission record payload to the institutional ERP endpoint."""
        pass


class MockERPAdapter(ERPAdapter):
    """
    Mock ERP adapter simulating enterprise synchronization with XYZ Engineering College ERP.
    Clearly labeled as PROTOTYPE / NO REAL ERP CONNECTION.
    """

    def sync_admission_record(
        self,
        staging_reference: str,
        payload: Dict[str, Any],
        simulate_failure: bool = False,
        failure_reason: str = None
    ) -> Dict[str, Any]:
        now_str = datetime.now(timezone.utc).isoformat()
        if simulate_failure:
            return {
                "success": False,
                "status": "SYNC_FAILED",
                "request_reference": staging_reference,
                "response_reference": None,
                "error_summary": failure_reason or "Mock ERP connection timeout: Institutional Student Registry endpoint unavailable.",
                "adapter": "MockERPAdapter",
                "synced_at": None,
                "is_prototype": True
            }

        erp_id = f"ERP-STUDENT-{uuid.uuid4().hex[:8].upper()}"
        return {
            "success": True,
            "status": "SYNCED",
            "request_reference": staging_reference,
            "response_reference": erp_id,
            "error_summary": None,
            "adapter": "MockERPAdapter",
            "synced_at": now_str,
            "details": {
                "college_code": "XYZ",
                "academic_year": "2026-27",
                "allocated_erp_roll_number": f"2026-XYZ-{uuid.uuid4().hex[:6].upper()}",
                "erp_record_id": erp_id,
                "message": "Mock ERP: Candidate successfully staged and ingested into academic student master registry."
            },
            "is_prototype": True
        }


# Global instance
mock_erp_adapter = MockERPAdapter()
