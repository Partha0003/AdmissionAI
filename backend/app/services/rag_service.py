import hashlib
import json
import math
import re
import time
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy import select, and_, desc, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.rag import (
    KnowledgeCategory,
    KnowledgeLifecycleState,
    ResponseType,
    ChatRole,
    KnowledgeDocument,
    KnowledgeDocumentVersion,
    KnowledgeChunk,
    ChatSession,
    ChatMessage,
    ChatAuditLog,
)
from app.models.admission import AdmissionApplication
from app.models.student import Student
from app.models.document import Document, DocumentVersion
from app.models.scrutiny import AdmissionReview
from app.models.physical_verification import PhysicalVerificationAppointment, PhysicalVerificationSession
from app.models.payment import PaymentTransaction, FeeRequirement
from app.models.erp import ERPAdmissionRecord
from app.models.onboarding import OnboardingProfile, OnboardingChecklistItem
from app.models.user import User
from app.adapters.llm_adapter import (
    LLMFactory,
    LLMProviderError,
    LLMPromptPayload,
    LLMResponse,
    RetrievedChunkPayload,
)
import uuid


# ==============================================================================
# 1. CHUNKING & EMBEDDING SERVICES
# ==============================================================================

class ChunkingService:
    """Splits knowledge content into semantic and section-aware chunks."""

    @staticmethod
    def chunk_document(content: str, max_chunk_tokens: int = 250, overlap_tokens: int = 30) -> List[Dict[str, Any]]:
        if not content or not content.strip():
            return []

        # Split by markdown/section headers if present
        sections = re.split(r'\n(?=#{1,3}\s+|\b[A-Z0-9\.\s]{4,30}:\n)', content)
        chunks: List[Dict[str, Any]] = []
        chunk_idx = 0

        for sec in sections:
            sec_text = sec.strip()
            if not sec_text:
                continue

            # Extract header if any
            first_line = sec_text.split('\n')[0]
            sec_title = first_line.replace('#', '').strip() if len(first_line) < 100 else "General Section"

            words = sec_text.split()
            if len(words) <= max_chunk_tokens:
                chunks.append({
                    "chunk_index": chunk_idx,
                    "section_title": sec_title,
                    "page_number": 1 + (chunk_idx // 3),
                    "content": sec_text,
                    "token_count": len(words),
                })
                chunk_idx += 1
            else:
                # Sliding window
                step = max(1, max_chunk_tokens - overlap_tokens)
                for i in range(0, len(words), step):
                    window_words = words[i:i + max_chunk_tokens]
                    window_text = " ".join(window_words)
                    chunks.append({
                        "chunk_index": chunk_idx,
                        "section_title": sec_title,
                        "page_number": 1 + (chunk_idx // 3),
                        "content": window_text,
                        "token_count": len(window_words),
                    })
                    chunk_idx += 1

        return chunks


class EmbeddingService:
    """
    Deterministic vector embedding generator for local vector operations.
    Produces 128-dimensional normalized float vectors.
    """

    DIMENSION = 128

    @classmethod
    def generate_embedding(cls, text: str) -> List[float]:
        if not text:
            return [0.0] * cls.DIMENSION

        # Tokenize and compute deterministic feature distribution
        tokens = re.findall(r'\w+', text.lower())
        vector = [0.0] * cls.DIMENSION

        for token in tokens:
            # Hash token across dimensions
            h = int(hashlib.md5(token.encode('utf-8')).hexdigest(), 16)
            dim_idx = h % cls.DIMENSION
            sign = 1.0 if ((h >> 8) & 1) == 0 else -1.0
            vector[dim_idx] += sign * (1.0 + (len(token) * 0.1))

        # L2 normalization
        norm = math.sqrt(sum(x * x for x in vector))
        if norm > 1e-9:
            vector = [round(x / norm, 6) for x in vector]
        return vector

    @classmethod
    def cosine_similarity(cls, vec_a: List[float], vec_b: List[float]) -> float:
        if not vec_a or not vec_b or len(vec_a) != len(vec_b):
            return 0.0
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))
        if norm_a < 1e-9 or norm_b < 1e-9:
            return 0.0
        return max(0.0, min(1.0, dot / (norm_a * norm_b)))


# ==============================================================================
# 2. LOCAL VECTOR STORE & RETRIEVER
# ==============================================================================

class LocalVectorStore:
    """Local vector store over PostgreSQL/SQLite active knowledge chunks."""

    @staticmethod
    async def search_active_chunks(
        db: AsyncSession,
        query: str,
        category: Optional[KnowledgeCategory] = None,
        top_k: int = 4,
        similarity_threshold: float = 0.15,
    ) -> List[RetrievedChunkPayload]:
        query_embedding = EmbeddingService.generate_embedding(query)

        # Query ONLY chunks belonging to ACTIVE document versions
        stmt = (
            select(KnowledgeChunk, KnowledgeDocumentVersion, KnowledgeDocument)
            .join(KnowledgeDocumentVersion, KnowledgeChunk.version_id == KnowledgeDocumentVersion.id)
            .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
            .where(
                and_(
                    KnowledgeDocumentVersion.lifecycle_state == KnowledgeLifecycleState.ACTIVE,
                )
            )
        )

        if category:
            stmt = stmt.where(KnowledgeDocument.category == category)

        result = await db.execute(stmt)
        rows = result.all()

        scored_chunks: List[Tuple[float, KnowledgeChunk, KnowledgeDocumentVersion, KnowledgeDocument]] = []

        query_tokens = set(re.findall(r'\w+', query.lower()))

        for chunk, version, doc in rows:
            chunk_emb = chunk.embedding_json
            if chunk_emb and isinstance(chunk_emb, list):
                sim = EmbeddingService.cosine_similarity(query_embedding, chunk_emb)
            else:
                sim = 0.0

            # Lexical keyword match bonus
            chunk_tokens = set(re.findall(r'\w+', chunk.content.lower()))
            common = query_tokens.intersection(chunk_tokens)
            lexical_boost = len(common) * 0.05
            combined_score = sim + lexical_boost

            if combined_score >= similarity_threshold:
                scored_chunks.append((combined_score, chunk, version, doc))

        # Sort descending by score
        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        top_matches = scored_chunks[:top_k]

        payloads: List[RetrievedChunkPayload] = []
        for score, chunk, version, doc in top_matches:
            payloads.append(
                RetrievedChunkPayload(
                    chunk_id=str(chunk.id),
                    document_id=str(doc.id),
                    document_title=doc.title,
                    document_category=doc.category.value if hasattr(doc.category, 'value') else str(doc.category),
                    version_number=version.version_number,
                    section_title=chunk.section_title,
                    page_number=chunk.page_number,
                    content=chunk.content,
                    score=round(score, 4),
                )
            )

        return payloads


# ==============================================================================
# 3. PRE-LLM SECURITY & PROMPT INJECTION FILTER
# ==============================================================================

class SecurityFilter:
    """Pre-LLM security and anti-IDOR filter."""

    INJECTION_PATTERNS = [
        r'ignore (all )?(previous|prior) instructions',
        r'reveal (your )?(system prompt|initial instructions)',
        r'disregard (privacy|security|system) rules',
        r'show (me )?(database|db) credentials',
        r'drop table',
        r'select \* from',
        r'show (all|other) students',
        r'give me (application|record) (xyz|alt|adm)',
        r'what is the password',
        r'bypass (auth|security)',
    ]

    CROSS_STUDENT_PATTERNS = [
        r'show (me )?(another|other) student',
        r'get student \w+',
        r'application (number )?[A-Za-z0-9_-]{8,30}',
        r'payment details of \w+',
    ]

    @classmethod
    def check_query_safety(cls, query: str, user_role: str) -> Tuple[bool, Optional[str]]:
        q_lower = query.lower()

        for pat in cls.INJECTION_PATTERNS:
            if re.search(pat, q_lower):
                return False, "Security Notice: This request attempts to override system safety rules or access restricted system internals and has been blocked."

        if user_role == "STUDENT":
            for pat in cls.CROSS_STUDENT_PATTERNS:
                if re.search(pat, q_lower):
                    # Check if querying another specific application
                    return False, "Privacy Notice: You may only query your own admission context. Accessing or requesting information regarding other applicants is strictly forbidden."

        return True, None


# ==============================================================================
# 4. CONTEXT RESOLVER
# ==============================================================================

class ContextResolver:
    """Extracts minimum necessary authorized student context for the user."""

    @staticmethod
    async def resolve_student_context(db: AsyncSession, user_id: str) -> Optional[Dict[str, Any]]:
        # Find student record
        stmt_student = select(Student).where(Student.user_id == user_id)
        res_s = await db.execute(stmt_student)
        student = res_s.scalar_one_or_none()

        if not student:
            return None

        # Find application
        stmt_app = select(AdmissionApplication).where(AdmissionApplication.student_id == student.id)
        res_a = await db.execute(stmt_app)
        app = res_a.scalar_one_or_none()

        if not app:
            return {
                "has_application": False,
                "student_name": student.full_name,
                "tnea_application_number": student.tnea_application_number,
                "status": "NOT_STARTED",
                "next_action": "Complete and submit your initial digital admission application.",
            }

        # Check documents & corrections
        stmt_docs = select(Document).where(Document.application_id == app.id)
        res_d = await db.execute(stmt_docs)
        docs = res_d.scalars().all()

        stmt_rev = select(AdmissionReview).where(AdmissionReview.application_id == app.id).order_by(desc(AdmissionReview.created_at))
        res_rev = await db.execute(stmt_rev)
        latest_rev = res_rev.scalars().first()

        pending_docs = []
        correction_docs = []
        for d in docs:
            doc_type_code = d.document_type.code if d.document_type else str(d.document_type_id)
            doc_name = d.document_type.name if d.document_type else doc_type_code
            if d.status in ["NOT_UPLOADED", "PROCESSING", "SUBMITTED"]:
                pending_docs.append({"code": doc_type_code, "name": doc_name, "status": d.status})
            elif d.status == "CORRECTION_REQUIRED":
                reason = "Reviewer adjustment requested"
                notes = "Please re-upload clearer certificate"
                if latest_rev:
                    for item in (latest_rev.document_reviews or []):
                        if item.document_id == d.id:
                            reason = item.correction_reason or reason
                            notes = item.reviewer_comments or notes
                            break
                    if reason == "Reviewer adjustment requested" and latest_rev.correction_instructions:
                        notes = latest_rev.correction_instructions
                correction_docs.append({
                    "code": doc_type_code,
                    "name": doc_name,
                    "reason": reason,
                    "notes": notes,
                })

        # Check physical verification
        stmt_pv = select(PhysicalVerificationAppointment).where(PhysicalVerificationAppointment.application_id == app.id)
        res_pv = await db.execute(stmt_pv)
        pv_appt = res_pv.scalars().first()

        # Check payment
        stmt_pay = select(PaymentTransaction).where(PaymentTransaction.application_id == app.id).order_by(desc(PaymentTransaction.created_at))
        res_pay = await db.execute(stmt_pay)
        active_payment = res_pay.scalars().first()

        # Check ERP
        stmt_erp = select(ERPAdmissionRecord).where(ERPAdmissionRecord.application_id == app.id)
        res_erp = await db.execute(stmt_erp)
        erp_rec = res_erp.scalar_one_or_none()

        blockers: List[str] = []
        next_action = "Continue your admission journey."

        if app.status in ["ALLOTTED", "ACTIVATED", "APPLICATION_IN_PROGRESS"]:
            blockers.append("Digital application form is incomplete.")
            next_action = "Complete and submit all 7 sections of the digital application form."
        elif correction_docs:
            blockers.append(f"{len(correction_docs)} document(s) require replacement.")
            next_action = "Re-upload the requested certificates in the Application Dossier."
        elif not pv_appt or pv_appt.appointment_status == "SCHEDULED":
            if not pv_appt:
                blockers.append("Physical verification appointment not booked.")
                next_action = "Schedule your on-site physical document check appointment."
            else:
                next_action = f"Attend on-site physical verification on {pv_appt.appointment_date} ({pv_appt.start_time}). Token #{pv_appt.token_number}."
        elif not active_payment or active_payment.status != "VERIFIED":
            if not active_payment:
                blockers.append("Admission fee payment pending.")
                next_action = "Submit your Demand Draft details or initiate demo online payment."
            elif active_payment.status == "CORRECTION_REQUIRED":
                blockers.append("DD submission details require correction.")
                next_action = "Resubmit updated Demand Draft details in the Fee Settlement section."
            else:
                next_action = "Awaiting Finance Officer verification of your submitted payment."
        elif not erp_rec or erp_rec.status != "SYNCED":
            next_action = "Your verified dossier is staged for institutional ERP synchronization."
        else:
            next_action = "Your admission is fully verified and synchronized into the institutional registry."

        # Check onboarding profile
        stmt_onb = select(OnboardingProfile).where(OnboardingProfile.student_id == student.id)
        res_onb = await db.execute(stmt_onb)
        onb_prof = res_onb.scalars().first()

        onboarding_context = None
        if onb_prof:
            student_type_str = onb_prof.student_type.value if hasattr(onb_prof.student_type, "value") else str(onb_prof.student_type)
            onboarding_context = {
                "onboarding_status": onb_prof.onboarding_status.value if hasattr(onb_prof.onboarding_status, "value") else str(onb_prof.onboarding_status),
                "student_type": student_type_str,
                "student_type_status": onb_prof.student_type_status.value if hasattr(onb_prof.student_type_status, "value") else str(onb_prof.student_type_status),
                "completion_percentage": onb_prof.overall_completion_percentage,
                "inauguration_date": "2026-08-31",
                "faculty_member_role": "Faculty Member",
            }

        return {
            "has_application": True,
            "application_id": str(app.id),
            "application_number": app.application_number or student.tnea_application_number,
            "student_name": student.full_name,
            "allotted_branch": student.allotted_branch,
            "status": app.status,
            "completion_percentage": app.completion_percentage,
            "blockers": blockers,
            "pending_documents": pending_docs,
            "correction_items": correction_docs,
            "onboarding": onboarding_context,
            "physical_verification": {
                "has_appointment": bool(pv_appt),
                "status": pv_appt.appointment_status if pv_appt else "NOT_SCHEDULED",
                "token": pv_appt.token_number if pv_appt else None,
                "date": pv_appt.appointment_date if pv_appt else None,
                "slot": f"{pv_appt.start_time} - {pv_appt.end_time}" if pv_appt else None,
                "location": pv_appt.location if pv_appt else "Main Admission Center",
            },
            "payment": {
                "status": active_payment.status if active_payment else "PENDING",
                "method": active_payment.payment_method if active_payment else None,
                "amount": float(active_payment.amount) if active_payment else 55000.0,
                "reference": active_payment.payment_reference if active_payment else None,
                "correction_reason": active_payment.rejection_reason if active_payment else None,
            },
            "erp": {
                "status": erp_rec.status if erp_rec else "NOT_READY",
                "staging_reference": erp_rec.staging_reference if erp_rec else None,
                "synced_at": erp_rec.synced_at.isoformat() if erp_rec and erp_rec.synced_at else None,
            },
            "next_action": next_action,
        }


# ==============================================================================
# 5. CITATION INTEGRITY VALIDATOR
# ==============================================================================

class CitationValidator:
    """Validates citations against the retrieved active chunk payload."""

    @staticmethod
    def validate_and_filter(
        emitted_citations: List[Dict[str, Any]],
        retrieved_chunks: List[RetrievedChunkPayload],
    ) -> List[Dict[str, Any]]:
        valid_chunk_ids = {c.chunk_id for c in retrieved_chunks}
        verified: List[Dict[str, Any]] = []

        for cite in emitted_citations:
            c_id = str(cite.get("chunk_id", ""))
            if c_id in valid_chunk_ids:
                verified.append(cite)

        return verified


# ==============================================================================
# 6. KNOWLEDGE BASE MANAGEMENT SERVICE
# ==============================================================================

class KnowledgeService:
    """Manages document ingestion, lifecycle states, chunking, and activation."""

    @classmethod
    async def ingest_document(
        cls,
        db: AsyncSession,
        title: str,
        content: str,
        category: KnowledgeCategory = KnowledgeCategory.GENERAL,
        description: Optional[str] = None,
        created_by_id: Optional[str] = None,
        auto_activate: bool = False,
    ) -> Tuple[KnowledgeDocument, KnowledgeDocumentVersion]:
        content_hash = hashlib.sha256(content.strip().encode("utf-8")).hexdigest()

        # Check if document exists with same title
        stmt_doc = select(KnowledgeDocument).where(KnowledgeDocument.title == title)
        res_doc = await db.execute(stmt_doc)
        doc = res_doc.scalar_one_or_none()

        if not doc:
            doc = KnowledgeDocument(
                id=str(uuid.uuid4()),
                title=title,
                category=category,
                description=description,
            )
            db.add(doc)
            await db.flush()
            version_num = 1
        else:
            # Determine next version number
            stmt_v = select(KnowledgeDocumentVersion).where(KnowledgeDocumentVersion.document_id == doc.id).order_by(desc(KnowledgeDocumentVersion.version_number))
            res_v = await db.execute(stmt_v)
            latest_v = res_v.scalars().first()
            version_num = (latest_v.version_number + 1) if latest_v else 1

            # Check duplicate content hash on latest
            if latest_v and latest_v.content_hash == content_hash and latest_v.lifecycle_state == KnowledgeLifecycleState.ACTIVE:
                return doc, latest_v

        # Create Version in DRAFT state
        version = KnowledgeDocumentVersion(
            id=str(uuid.uuid4()),
            document_id=doc.id,
            version_number=version_num,
            lifecycle_state=KnowledgeLifecycleState.PROCESSING,
            content=content,
            content_hash=content_hash,
            created_by_id=created_by_id,
        )
        db.add(version)
        await db.flush()

        # Chunk and embed
        raw_chunks = ChunkingService.chunk_document(content)
        for c in raw_chunks:
            emb = EmbeddingService.generate_embedding(c["content"])
            chunk_rec = KnowledgeChunk(
                id=str(uuid.uuid4()),
                document_id=doc.id,
                version_id=version.id,
                chunk_index=c["chunk_index"],
                section_title=c["section_title"],
                page_number=c["page_number"],
                content=c["content"],
                embedding_json=emb,
                token_count=c["token_count"],
            )
            db.add(chunk_rec)

        version.lifecycle_state = KnowledgeLifecycleState.READY

        if auto_activate:
            # Archive previous active versions
            await db.execute(
                update(KnowledgeDocumentVersion)
                .where(
                    and_(
                        KnowledgeDocumentVersion.document_id == doc.id,
                        KnowledgeDocumentVersion.id != version.id,
                        KnowledgeDocumentVersion.lifecycle_state == KnowledgeLifecycleState.ACTIVE,
                    )
                )
                .values(
                    lifecycle_state=KnowledgeLifecycleState.ARCHIVED,
                    archived_at=datetime.utcnow(),
                )
            )
            version.lifecycle_state = KnowledgeLifecycleState.ACTIVE
            version.activated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(doc)
        await db.refresh(version)
        return doc, version

    @classmethod
    async def activate_version(cls, db: AsyncSession, version_id: str) -> KnowledgeDocumentVersion:
        stmt = select(KnowledgeDocumentVersion).where(KnowledgeDocumentVersion.id == version_id)
        res = await db.execute(stmt)
        ver = res.scalar_one_or_none()
        if not ver:
            raise ValueError(f"KnowledgeDocumentVersion '{version_id}' not found.")

        # Archive other active versions of this document
        await db.execute(
            update(KnowledgeDocumentVersion)
            .where(
                and_(
                    KnowledgeDocumentVersion.document_id == ver.document_id,
                    KnowledgeDocumentVersion.id != ver.id,
                    KnowledgeDocumentVersion.lifecycle_state == KnowledgeLifecycleState.ACTIVE,
                )
            )
            .values(
                lifecycle_state=KnowledgeLifecycleState.ARCHIVED,
                archived_at=datetime.utcnow(),
            )
        )

        ver.lifecycle_state = KnowledgeLifecycleState.ACTIVE
        ver.activated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(ver)
        return ver

    @classmethod
    async def seed_initial_knowledge(cls, db: AsyncSession) -> None:
        """Seed approved prototype knowledge base for XYZ Engineering College."""
        stmt = select(KnowledgeDocument)
        res = await db.execute(stmt)
        if res.first():
            return  # Already seeded

        documents = [
            (
                "XYZ Admission & Eligibility Policy 2026–27",
                KnowledgeCategory.ADMISSION_GUIDELINES,
                """# XYZ Engineering College Admission Guidelines
## Section 1: Overview
XYZ Engineering College (College Code: XYZ) conducts admissions for Academic Year 2026–27 strictly via authorized single-window counselling (TNEA) and approved institutional quota channels.

## Section 2: Mandatory Milestones
Every candidate must complete the following sequential milestones:
1. Candidate Activation: Verify allotment order and activate portal login.
2. Digital Application: Fill 7 sections of the admission form and upload original certificates.
3. Digital Scrutiny Desk: Admission officers review uploaded certificates for legibility and quota consistency.
4. Physical Verification: Present original certificates in person at XYZ campus.
5. Fee Settlement: Submit Demand Draft or complete demo online payment.
6. ERP Synchronization: Institutional confirmation and student ID generation.
""",
            ),
            (
                "Required Certificates & Document Checklist",
                KnowledgeCategory.DOCUMENT_VERIFICATION,
                """# Certificate Verification Guidelines
## Section 1: Mandatory Certificates
All candidates must submit clear scanned copies of:
- 10th Standard Marksheet (Proof of Date of Birth)
- 12th Standard HSC / Equivalent Marksheet (Cutoff and Subject Marks)
- Community Certificate (for BC, BCM, MBC, SC, SCA, ST quota claims)
- Transfer Certificate (TC) issued by the last attended institution
- TNEA Provisional Allotment Order

## Section 2: Special Quota Documents
- First Graduate Certificate & Joint Declaration (if claiming First Graduate fee waiver)
- 7.5% Government School Quota Bonafide Certificate (for 6th to 12th government school students)
- Income Certificate (for PMSS and fee concession eligibility)
""",
            ),
            (
                "Campus Physical Verification & Appointment Guide",
                KnowledgeCategory.PHYSICAL_VERIFICATION,
                """# Campus Physical Verification Process
## Section 1: Scheduling and Venue
Physical document check takes place at the Main Admission Hall, Ground Floor, XYZ Engineering College. Candidates must book an appointment slot through their dashboard.

## Section 2: What to Bring
Candidates must bring:
1. All original certificates corresponding to the digital uploads.
2. 4 passport-size photographs.
3. 2 sets of self-attested photocopies of all documents.
4. Check-in QR Token Pass generated on the portal.

## Section 3: Token Check-In
Upon arrival, present the QR pass at the Check-In Desk to receive a physical queue token. The verification officer will inspect originals and record verification decisions.
""",
            ),
            (
                "Fee Structure & Demand Draft Settlement Guide",
                KnowledgeCategory.FEE_AND_PAYMENT,
                """# Fee Payment and Demand Draft Guidelines
## Section 1: Authoritative Fee Structure
The standard tuition and development fee requirement for Academic Year 2026–27 is ₹55,000 INR for Government Quota (General) candidates. First Graduate concession is applied per government norms.

## Section 2: Demand Draft (DD) Specifications
- Demand Draft must be drawn in favor of 'XYZ Engineering College' payable at Chennai.
- Ensure DD number (6 digits), issue date, and bank branch are entered accurately into the portal.
- Upload a clear scan of the DD counterfoil/receipt.

## Section 3: Finance Desk Review
The College Finance Officer reconciles the submitted DD details against the physical instrument. Status updates to VERIFIED once approved.
""",
            ),
            (
                "Frequently Asked Questions (FAQ)",
                KnowledgeCategory.FAQ,
                """# Frequently Asked Questions
## Question 1: What is Digital Scrutiny?
Digital Scrutiny is the preliminary document check performed online by the college admission desk to ensure your certificates are legible and valid before your campus visit.

## Question 2: What if my document is sent for correction?
If an officer requests correction, your status will change to CORRECTION_REQUIRED. You must review the officer's specific instructions in your dashboard and upload an updated certificate.

## Question 3: Can I pay fees before physical verification?
Under standard college policy, fee settlement is completed after or alongside successful physical certificate verification.

## Question 4: How do I know my admission is confirmed?
Admission is confirmed when both Physical Verification and Fee Settlement are VERIFIED, and your record is staged and synced to the Institutional ERP.
""",
            ),
            (
                "First-Year Student & Parent Onboarding Guidelines",
                KnowledgeCategory.FIRST_YEAR_ONBOARDING,
                """# General Instructions to be informed to all students
## Section 1: First-Year Inauguration Ceremony
The First-Year Inauguration Ceremony is scheduled for 31.08.2026 at the Main College Auditorium. Reporting time is 08:30 AM. Both students and parents are cordially invited.

## Section 2: Faculty Member & Counsellor Mentorship
Every first-year student is assigned a dedicated Faculty Member and department counsellor for continuous academic and personal mentorship.

## Section 3: Official Academic Communication Channel
The primary academic communication channel with parents is the Official Parents' WhatsApp Group, through which attendance and performance circulars are shared.

## Section 4: Recommended Laptop Specifications
Students are advised to equip themselves with laptops configured with Intel Core i5 or AMD Ryzen 5, 16GB RAM, and 512GB SSD for engineering coursework.

## Section 5: Campus Dress Code Policy
Boys must wear formal shirts tucked in with formal trousers and leather shoes. Girls must wear formal churidar/salwar kameez with dupatta pinned on both sides.

## Section 6: Placement Record Disclosure
Institution-Provided Information (Not independently verified by AdmissionAI): The institution highlights an 85% placement record for eligible students across leading technical recruiters.
""",
            ),
            (
                "Hosteller Life, Rules & Mobile Phone Guidance",
                KnowledgeCategory.HOSTELLER,
                """# Hosteller Code of Conduct & Guidelines
## Section 1: Hosteller mobile-phone guidance
Hosteller mobile-phone guidance: Mobile usage is permitted in hostel rooms during non-study hours and strictly forbidden during study hours (08:30 PM - 10:30 PM).

## Section 2: Food & Delivery Policy
Outside cooked food delivery is strictly prohibited inside the hostel premises. Wholesome dining is provided in the mess.

## Section 3: Visitors & Outpass
Parents must submit the Authorized Visitors' Form with photographs at check-in. Any leave or outpass requires Resident Warden approval and parent verification.

## Section 4: Personal Necessities
Students should bring their own mattress, pillow, bedsheets, bucket, mug, lock & keys, and study lamp.
""",
            ),
            (
                "Day-Scholar Transportation & Conduct Guidelines",
                KnowledgeCategory.DAY_SCHOLAR,
                """# Day-Scholar Transportation & Rules
## Section 1: College Bus Transport
Day scholars utilizing college transport must board at designated stops with valid bus passes and maintain punctual boarding habits.

## Section 2: Mobile Usage Policy
Day scholars must keep mobile phones switched off and stowed inside bags during all academic hours.
""",
            ),
        ]

        for title, cat, text in documents:
            await cls.ingest_document(
                db,
                title=title,
                content=text,
                category=cat,
                auto_activate=True,
            )


# ==============================================================================
# 7. CHAT & RAG ORCHESTRATION SERVICE
# ==============================================================================

def get_user_role_str(user_or_role: Any) -> str:
    if not user_or_role:
        return "STUDENT"
    if isinstance(user_or_role, str):
        return user_or_role
    if hasattr(user_or_role, "role"):
        r = user_or_role.role
        if isinstance(r, str):
            return r
        if hasattr(r, "name"):
            return str(r.name)
    if hasattr(user_or_role, "name"):
        return str(user_or_role.name)
    return str(user_or_role)


class ChatService:
    """Orchestrates RAG chat pipeline with strict isolation, grounding, and audit."""

    @classmethod
    async def create_session(
        cls,
        db: AsyncSession,
        user: User,
        title: str = "Admission Support",
    ) -> ChatSession:
        role_str = get_user_role_str(user)
        # Find user's linked application if student
        app_id = None
        if role_str == "STUDENT":
            stmt_s = select(Student).where(Student.user_id == user.id)
            res_s = await db.execute(stmt_s)
            student = res_s.scalar_one_or_none()
            if student:
                stmt_a = select(AdmissionApplication).where(AdmissionApplication.student_id == student.id)
                res_a = await db.execute(stmt_a)
                app = res_a.scalar_one_or_none()
                if app:
                    app_id = app.id

        session = ChatSession(
            id=str(uuid.uuid4()),
            user_id=user.id,
            application_id=app_id,
            title=title,
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session

    @classmethod
    async def get_user_sessions(cls, db: AsyncSession, user_id: str) -> List[ChatSession]:
        stmt = (
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .order_by(desc(ChatSession.created_at))
        )
        res = await db.execute(stmt)
        return res.scalars().all()

    @classmethod
    async def get_session_detail(cls, db: AsyncSession, session_id: str, user_id: str, user_role: Any) -> Optional[ChatSession]:
        stmt = (
            select(ChatSession)
            .where(ChatSession.id == session_id)
            .options(selectinload(ChatSession.messages))
        )
        res = await db.execute(stmt)
        session = res.scalar_one_or_none()
        if not session:
            return None

        role_str = get_user_role_str(user_role)
        # Anti-IDOR: Student can only view own session
        if role_str == "STUDENT" and str(session.user_id) != str(user_id):
            return None

        return session

    @classmethod
    async def process_user_message(
        cls,
        db: AsyncSession,
        session_id: str,
        user: User,
        query: str,
        llm_provider: str = "mock",
        top_k: int = 4,
    ) -> ChatMessage:
        start_time = time.perf_counter()
        role_str = get_user_role_str(user)

        # 1. Validate Session & Anti-IDOR
        session = await cls.get_session_detail(db, session_id, user.id, role_str)
        if not session:
            raise ValueError("Chat session not found or unauthorized.")

        # 2. Record User Message
        user_msg = ChatMessage(
            id=str(uuid.uuid4()),
            session_id=session.id,
            user_id=user.id,
            sender_role=ChatRole.USER,
            message=query.strip(),
        )
        db.add(user_msg)
        await db.flush()

        # 3. Pre-LLM Security & Anti-IDOR Filter
        is_safe, refusal_reason = SecurityFilter.check_query_safety(query, role_str)
        if not is_safe:
            assistant_msg = ChatMessage(
                id=str(uuid.uuid4()),
                session_id=session.id,
                user_id=user.id,
                sender_role=ChatRole.ASSISTANT,
                message=refusal_reason or "Request refused by security policy.",
                response_type=ResponseType.SECURITY_REFUSAL,
                retrieved_sources_json=[],
                personal_context_used_json=None,
                latency_ms=round((time.perf_counter() - start_time) * 1000.0, 2),
            )
            db.add(assistant_msg)

            # Audit log
            audit = ChatAuditLog(
                id=str(uuid.uuid4()),
                user_id=user.id,
                user_role=role_str,
                session_id=session.id,
                message_id=assistant_msg.id,
                query_preview=query[:500],
                query_category="SECURITY_REFUSAL",
                retrieved_source_ids_json=[],
                response_status="REFUSED",
                model_provider="security_filter",
                latency_ms=assistant_msg.latency_ms,
            )
            db.add(audit)
            await db.commit()
            await db.refresh(assistant_msg)
            return assistant_msg

        # 4. Context Resolver: Minimal Authorized Context
        personal_context = None
        if role_str == "STUDENT":
            personal_context = await ContextResolver.resolve_student_context(db, user.id)

        # 5. Retrieve Active Knowledge Chunks
        retrieved_chunks = await LocalVectorStore.search_active_chunks(
            db=db,
            query=query,
            top_k=top_k,
        )

        # 6. LLM Execution via Adapter
        try:
            adapter = LLMFactory.get_adapter(llm_provider)
            prompt_payload = LLMPromptPayload(
                user_query=query,
                user_role=role_str,
                personal_context=personal_context,
                retrieved_chunks=retrieved_chunks,
            )
            llm_response = adapter.generate(prompt_payload)
        except LLMProviderError as e:
            # Explicit error handling: return SYSTEM_ERROR without silent fallback
            assistant_msg = ChatMessage(
                id=str(uuid.uuid4()),
                session_id=session.id,
                user_id=user.id,
                sender_role=ChatRole.ASSISTANT,
                message=f"System Error: The requested AI LLM provider '{llm_provider}' is currently unavailable. ({str(e)})",
                response_type=ResponseType.SYSTEM_ERROR,
                retrieved_sources_json=[],
                personal_context_used_json=None,
                latency_ms=round((time.perf_counter() - start_time) * 1000.0, 2),
            )
            db.add(assistant_msg)
            audit = ChatAuditLog(
                id=str(uuid.uuid4()),
                user_id=user.id,
                user_role=role_str,
                session_id=session.id,
                message_id=assistant_msg.id,
                query_preview=query[:500],
                query_category="SYSTEM_ERROR",
                retrieved_source_ids_json=[],
                response_status="ERROR",
                model_provider=llm_provider,
                latency_ms=assistant_msg.latency_ms,
            )
            db.add(audit)
            await db.commit()
            await db.refresh(assistant_msg)
            return assistant_msg

        # 7. Citation Integrity Validation
        verified_citations = CitationValidator.validate_and_filter(
            llm_response.citations,
            retrieved_chunks,
        )

        total_latency = (time.perf_counter() - start_time) * 1000.0

        # 8. Record Assistant Message
        assistant_msg = ChatMessage(
            id=str(uuid.uuid4()),
            session_id=session.id,
            user_id=user.id,
            sender_role=ChatRole.ASSISTANT,
            message=llm_response.answer,
            response_type=llm_response.response_type,
            retrieved_sources_json=verified_citations,
            personal_context_used_json={"used": llm_response.personal_context_used, "app_status": personal_context.get("status") if personal_context else None} if llm_response.personal_context_used else None,
            latency_ms=round(total_latency, 2),
        )
        db.add(assistant_msg)

        # 9. Append-Only Chat Audit Log
        audit = ChatAuditLog(
            id=str(uuid.uuid4()),
            user_id=user.id,
            user_role=role_str,
            session_id=session.id,
            message_id=assistant_msg.id,
            query_preview=query[:500],
            query_category="ADMISSION_ASSISTANT",
            retrieved_source_ids_json=[c["chunk_id"] for c in verified_citations],
            response_status="SUCCESS",
            model_provider=llm_response.model_provider,
            latency_ms=round(total_latency, 2),
        )
        db.add(audit)

        await db.commit()
        await db.refresh(assistant_msg)
        return assistant_msg
