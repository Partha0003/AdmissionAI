from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple, Optional
from datetime import date, datetime


class AllotmentValidationError(Exception):
    """Exception raised when an allotment record fails deterministic validation."""
    def __init__(self, message: str, record: Optional[Dict[str, Any]] = None, errors: Optional[List[str]] = None):
        super().__init__(message)
        self.message = message
        self.record = record or {}
        self.errors = errors or []


class TNEAAdapter(ABC):
    """
    Abstract Base Class for TNEA Allotment Ingestion.
    Decouples the core AdmissionAI application from external TNEA data sources.
    Future live integrations will implement this interface without modifying business workflows.
    """

    @abstractmethod
    def validate_record(self, record: Dict[str, Any], target_institution_code: str) -> Tuple[bool, List[str]]:
        """
        Deterministically validates an incoming allotment record.
        Returns: (is_valid, list_of_error_strings)
        """
        pass

    @abstractmethod
    def parse_allotments(
        self, raw_data: List[Dict[str, Any]], target_institution_code: str
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Processes raw allotment data.
        Returns: (valid_records, rejected_wrong_institution, invalid_records)
        """
        pass


class MockTNEAAdapter(TNEAAdapter):
    """
    Mock implementation of TNEAAdapter using synthetic demo records for XYZ Engineering College.
    Strictly simulated; does NOT scrape or access external TNEA servers.
    """

    MANDATORY_FIELDS = [
        "tnea_application_number",
        "allotment_number",
        "student_name",
        "college_code",
        "college_name",
        "branch_name",
        "allotment_date",
        "joining_deadline",
        "allotment_status",
    ]

    def validate_record(self, record: Dict[str, Any], target_institution_code: str) -> Tuple[bool, List[str]]:
        errors: List[str] = []

        # 1. Mandatory field checks
        for field in self.MANDATORY_FIELDS:
            val = record.get(field)
            if val is None or (isinstance(val, str) and not val.strip()):
                errors.append(f"Missing mandatory field '{field}'")

        # 2. Institution code match
        college_code = str(record.get("college_code", "")).strip()
        if college_code and college_code.upper() != target_institution_code.upper():
            errors.append(
                f"Institution mismatch: Allotment is for '{college_code}', but target institution is '{target_institution_code}'"
            )

        # 3. Date format validation
        for date_field in ["allotment_date", "joining_deadline", "date_of_birth"]:
            val = record.get(date_field)
            if val:
                try:
                    if isinstance(val, str):
                        date.fromisoformat(val)
                except ValueError:
                    errors.append(f"Invalid ISO date format for '{date_field}': '{val}'. Expected YYYY-MM-DD")

        # 4. Email format check if provided
        email = record.get("email")
        if email and ("@" not in email or "." not in email):
            errors.append(f"Invalid email format: '{email}'")

        return len(errors) == 0, errors

    def parse_allotments(
        self, raw_data: List[Dict[str, Any]], target_institution_code: str
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        valid_records: List[Dict[str, Any]] = []
        wrong_institution_records: List[Dict[str, Any]] = []
        invalid_records: List[Dict[str, Any]] = []

        for record in raw_data:
            college_code = str(record.get("college_code", "")).strip().upper()
            if college_code and college_code != target_institution_code.upper():
                wrong_institution_records.append({
                    "record": record,
                    "reason": f"Allotment is for institution '{college_code}', expected '{target_institution_code}'"
                })
                continue

            is_valid, errors = self.validate_record(record, target_institution_code)
            if is_valid:
                valid_records.append(record)
            else:
                invalid_records.append({
                    "record": record,
                    "errors": errors
                })

        return valid_records, wrong_institution_records, invalid_records
