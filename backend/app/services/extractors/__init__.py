from __future__ import annotations

from typing import Dict, Type
from app.services.extractors.base import (
    FieldExtractor,
    ExtractedField,
    ExtractionResultData,
    FieldSourceProvenance,
    FieldExtractionException,
    ExtractorNotFoundException,
)
from app.services.extractors.twelfth_marksheet import TwelfthMarksheetExtractor
from app.services.extractors.tenth_marksheet import TenthMarksheetExtractor
from app.services.extractors.community_certificate import CommunityCertificateExtractor
from app.services.extractors.allotment_order import AllotmentOrderExtractor
from app.services.extractors.certificate_extractors import (
    TransferCertificateExtractor,
    IncomeCertificateExtractor,
    FirstGraduateCertificateExtractor,
)
from app.services.extractors.generic_extractor import GenericDocumentExtractor

# Registry mapping document_type_code to specialized extractor instance
_EXTRACTORS: Dict[str, FieldExtractor] = {
    "TWELFTH_MARKSHEET": TwelfthMarksheetExtractor(),
    "TENTH_MARKSHEET": TenthMarksheetExtractor(),
    "COMMUNITY_CERTIFICATE": CommunityCertificateExtractor(),
    "ALLOTMENT_ORDER": AllotmentOrderExtractor(),
    "TRANSFER_CERTIFICATE": TransferCertificateExtractor(),
    "INCOME_CERTIFICATE": IncomeCertificateExtractor(),
    "FIRST_GRADUATE_CERTIFICATE": FirstGraduateCertificateExtractor(),
}

_GENERIC_EXTRACTOR = GenericDocumentExtractor()


class FieldExtractorFactory:
    """
    Factory for retrieving document-type-specific field extractors with generic fallback.
    """

    @classmethod
    def get_extractor(cls, document_type_code: str) -> FieldExtractor:
        if not document_type_code:
            return _GENERIC_EXTRACTOR
        clean_code = document_type_code.strip().upper()
        return _EXTRACTORS.get(clean_code, _GENERIC_EXTRACTOR)


__all__ = [
    "FieldExtractor",
    "ExtractedField",
    "ExtractionResultData",
    "FieldSourceProvenance",
    "FieldExtractionException",
    "ExtractorNotFoundException",
    "TwelfthMarksheetExtractor",
    "TenthMarksheetExtractor",
    "CommunityCertificateExtractor",
    "AllotmentOrderExtractor",
    "TransferCertificateExtractor",
    "IncomeCertificateExtractor",
    "FirstGraduateCertificateExtractor",
    "GenericDocumentExtractor",
    "FieldExtractorFactory",
]
