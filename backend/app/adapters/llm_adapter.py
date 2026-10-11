from abc import ABC, abstractmethod
import time
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from app.models.rag import ResponseType


@dataclass
class RetrievedChunkPayload:
    chunk_id: str
    document_id: str
    document_title: str
    document_category: str
    version_number: int
    section_title: Optional[str]
    page_number: Optional[int]
    content: str
    score: float


@dataclass
class LLMPromptPayload:
    user_query: str
    user_role: str
    personal_context: Optional[Dict[str, Any]] = None
    retrieved_chunks: List[RetrievedChunkPayload] = field(default_factory=list)
    intent: str = "GENERAL"


@dataclass
class LLMResponse:
    answer: str
    response_type: ResponseType
    citations: List[Dict[str, Any]]
    model_provider: str
    latency_ms: float
    personal_context_used: bool


class LLMProviderError(Exception):
    """Raised when an external or configured LLM provider fails or is unreachable."""
    pass


class LLMAdapter(ABC):
    @abstractmethod
    def generate(self, payload: LLMPromptPayload) -> LLMResponse:
        """Generate a grounded response strictly from the provided payload."""
        pass


class MockLLMAdapter(LLMAdapter):
    """
    Deterministic Mock LLM Adapter.
    Strictly bounded: Operates ONLY on the provided payload (personal_context + retrieved_chunks).
    Performs zero independent database lookups.
    """

    def generate(self, payload: LLMPromptPayload) -> LLMResponse:
        start_time = time.perf_counter()
        query = payload.user_query.lower()
        context = payload.personal_context or {}
        chunks = payload.retrieved_chunks or []

        citations: List[Dict[str, Any]] = []
        for c in chunks:
            citations.append({
                "chunk_id": c.chunk_id,
                "document_id": c.document_id,
                "document_title": c.document_title,
                "section_title": c.section_title or "General Section",
                "page_number": c.page_number,
                "version_number": c.version_number,
                "category": c.document_category,
            })

        has_personal = bool(context and context.get("has_application"))
        has_knowledge = bool(chunks)

        # 1. Check for personal context queries
        is_next_action = any(k in query for k in ["next", "what should i do", "what to do", "next step"])
        is_pending_docs = any(k in query for k in ["pending document", "documents pending", "what documents", "certificates pending"])
        is_correction_query = any(k in query for k in ["correction", "why correction", "resubmit", "rejected document"])
        is_status_query = any(k in query for k in ["my status", "admission status", "why can't i complete", "why cannot i complete", "where am i"])
        is_payment_query = any(k in query for k in ["have i completed payment", "my payment", "payment status", "did i pay"])
        is_pv_query = any(k in query for k in ["when should i come", "my physical verification", "my appointment", "my token"])

        answer_parts: List[str] = []
        resp_type = ResponseType.GROUNDED_KNOWLEDGE
        personal_used = False

        if has_personal and (is_next_action or is_pending_docs or is_correction_query or is_status_query or is_payment_query or is_pv_query):
            personal_used = True
            app_no = context.get("application_number", "N/A")
            status = context.get("status", "NOT_STARTED")
            blockers = context.get("blockers", [])
            pending_docs = context.get("pending_documents", [])
            corrections = context.get("correction_items", [])
            pv_state = context.get("physical_verification", {})
            pay_state = context.get("payment", {})
            erp_state = context.get("erp", {})
            next_action = context.get("next_action", "Check with admission desk.")

            if is_next_action:
                answer_parts.append(
                    f"Based on your current admission status ({status}) for Application #{app_no}, your next recommended action is: {next_action}"
                )
                if blockers:
                    answer_parts.append(f"\nActive items requiring attention:\n- " + "\n- ".join(blockers))
            elif is_pending_docs:
                if pending_docs or corrections:
                    answer_parts.append(f"Here are the documents pending or requiring replacement for Application #{app_no}:")
                    for d in pending_docs:
                        answer_parts.append(f"- {d.get('name')} (Status: {d.get('status')})")
                    for c in corrections:
                        answer_parts.append(f"- {c.get('name')}: Requires correction. Reason: {c.get('reason')} (Notes: '{c.get('notes')}')")
                else:
                    answer_parts.append(f"All mandatory documents for Application #{app_no} have been uploaded and resolved.")
            elif is_correction_query:
                if corrections:
                    answer_parts.append(f"Your document review noted the following correction requirement(s):")
                    for c in corrections:
                        answer_parts.append(f"- Document: {c.get('name')}\n  Reason: {c.get('reason')}\n  Reviewer Instructions: \"{c.get('notes')}\"")
                    answer_parts.append("\nPlease navigate to the Application Dossier to upload the corrected certificate version.")
                else:
                    answer_parts.append(f"There are currently no active document correction requests on file for Application #{app_no}.")
            elif is_payment_query:
                pay_status = pay_state.get("status", "NOT_INITIATED")
                amount = pay_state.get("amount", 55000)
                method = pay_state.get("method", "N/A")
                ref = pay_state.get("reference", "N/A")
                if pay_status == "VERIFIED":
                    answer_parts.append(f"Your admission fee payment of ₹{amount:,.2f} via {method} (Ref: {ref}) has been VERIFIED by the Finance Desk.")
                elif pay_status in ["SUBMITTED", "UNDER_REVIEW"]:
                    answer_parts.append(f"Your payment transaction (Ref: {ref}) is currently SUBMITTED / UNDER REVIEW by the Finance Desk.")
                elif pay_status == "CORRECTION_REQUIRED":
                    answer_parts.append(f"Your payment requires correction. Reason: {pay_state.get('correction_reason', 'Details mismatch')}. Please resubmit your DD details.")
                else:
                    answer_parts.append(f"Your admission fee payment is currently {pay_status}. Configured payable amount: ₹{amount:,.2f} INR.")
            elif is_pv_query:
                token = pv_state.get("token")
                date = pv_state.get("date")
                slot = pv_state.get("slot")
                loc = pv_state.get("location", "Admission Hall")
                pv_status = pv_state.get("status", "NOT_SCHEDULED")
                if token and date:
                    answer_parts.append(f"Your physical document verification is scheduled for {date} ({slot}) at {loc}. Your Token Number is #{token} (Status: {pv_status}).")
                else:
                    answer_parts.append(f"You have not scheduled a physical verification slot yet. Please select an available date in your dashboard.")
            else:
                answer_parts.append(f"Your AdmissionAI record status is currently: {status}.")
                if blockers:
                    answer_parts.append(f"Blockers: " + "; ".join(blockers))

            # Combine with knowledge if available
            if has_knowledge:
                resp_type = ResponseType.GROUNDED_KNOWLEDGE_PLUS_PERSONAL_CONTEXT
                answer_parts.append("\nInstitutional Guidelines:")
                for c in chunks[:2]:
                    answer_parts.append(f"- {c.content.strip()}")
            else:
                resp_type = ResponseType.PERSONAL_CONTEXT

        elif has_knowledge:
            # Pure knowledge query
            resp_type = ResponseType.GROUNDED_KNOWLEDGE
            answer_parts.append("According to the approved XYZ Engineering College Admission Guidelines:")
            for c in chunks[:3]:
                sec_header = f"[{c.document_title} - {c.section_title or 'Guidelines'}]"
                answer_parts.append(f"\n{sec_header}\n{c.content.strip()}")
        else:
            # Insufficient evidence
            resp_type = ResponseType.INSUFFICIENT_EVIDENCE
            answer_parts.append(
                "I couldn't find this information in the approved AdmissionAI knowledge base for XYZ Engineering College, and no relevant admission context was available."
            )

        latency_ms = (time.perf_counter() - start_time) * 1000.0

        return LLMResponse(
            answer="\n".join(answer_parts),
            response_type=resp_type,
            citations=citations if has_knowledge else [],
            model_provider="mock",
            latency_ms=round(latency_ms, 2),
            personal_context_used=personal_used,
        )


class LLMFactory:
    """Factory to retrieve configured LLM adapter with explicit failure handling."""

    @staticmethod
    def get_adapter(provider_name: str = "mock") -> LLMAdapter:
        provider = (provider_name or "mock").lower()
        if provider == "mock":
            return MockLLMAdapter()
        elif provider in ["gemini", "openai"]:
            # Real provider configured: raise LLMProviderError if API key or service is unavailable
            raise LLMProviderError(f"External LLM provider '{provider}' is not reachable or unconfigured in prototype mode.")
        else:
            raise LLMProviderError(f"Unknown LLM provider '{provider}' requested.")
