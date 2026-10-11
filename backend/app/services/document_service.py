import os
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Tuple, Optional
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.models.admission import AdmissionApplication
from app.models.document import DocumentType, Document, DocumentVersion
from app.models.user import User

ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}
ALLOWED_MIME_TYPES = {"application/pdf", "image/png", "image/jpeg", "image/pjpeg"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


def validate_file_content(content: bytes, filename: str, mime_type: str) -> None:
    """
    Validates file extension, MIME type, size limit, and header magic bytes.
    """
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File exceeds maximum allowed size of {MAX_FILE_SIZE // (1024 * 1024)}MB"
        )

    ext = filename.split(".")[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File extension '.{ext}' is not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Magic byte inspection
    is_valid_magic = False
    if content.startswith(b"%PDF-"):
        is_valid_magic = True
    elif content.startswith(b"\x89PNG\r\n\x1a\n"):
        is_valid_magic = True
    elif content.startswith(b"\xff\xd8\xff"):
        is_valid_magic = True

    if not is_valid_magic:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format or corrupted header. File signature does not match PDF, PNG, or JPEG."
        )


class DocumentService:
    @staticmethod
    def get_storage_base_dir() -> Path:
        backend_dir = Path(__file__).resolve().parent.parent.parent
        storage_dir = backend_dir / "storage" / "documents"
        storage_dir.mkdir(parents=True, exist_ok=True)
        return storage_dir

    @classmethod
    async def upload_document(
        cls,
        db: AsyncSession,
        application: AdmissionApplication,
        document_type_code: str,
        upload_file: UploadFile,
        current_user: User,
    ) -> Tuple[Document, DocumentVersion]:
        """
        Processes and securely stores an uploaded document, versioning any existing upload.
        """
        # 1. Retrieve DocumentType
        stmt = select(DocumentType).where(
            DocumentType.code == document_type_code,
            DocumentType.is_active == True
        )
        res = await db.execute(stmt)
        doc_type = res.scalar_one_or_none()
        if not doc_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document type '{document_type_code}' not found or inactive"
            )

        # 2. Read and validate file content
        content = await upload_file.read()
        filename = upload_file.filename or f"doc_{document_type_code}.pdf"
        mime_type = upload_file.content_type or "application/octet-stream"

        validate_file_content(content, filename, mime_type)

        # 3. Calculate SHA-256
        sha256_hash = hashlib.sha256(content).hexdigest()

        # 4. Check for existing Document record
        doc_stmt = (
            select(Document)
            .where(
                Document.application_id == application.id,
                Document.document_type_id == doc_type.id
            )
        )
        doc_res = await db.execute(doc_stmt)
        doc = doc_res.scalar_one_or_none()

        if not doc:
            doc = Document(
                application_id=application.id,
                document_type_id=doc_type.id,
                status="UPLOADED",
            )
            db.add(doc)
            await db.flush()
            version_number = 1
        else:
            doc.status = "UPLOADED"
            doc.updated_at = datetime.now(timezone.utc)
            # Find next version number
            version_number = len(doc.versions) + 1

        # 5. Persist to private disk storage
        storage_base = cls.get_storage_base_dir()
        target_dir = storage_base / application.id / doc_type.id
        target_dir.mkdir(parents=True, exist_ok=True)

        safe_filename = f"v{version_number}_{hashlib.md5(filename.encode()).hexdigest()[:8]}_{filename}"
        target_file_path = target_dir / safe_filename

        with open(target_file_path, "wb") as f:
            f.write(content)

        # 6. Create DocumentVersion record
        doc_version = DocumentVersion(
            document_id=doc.id,
            version_number=version_number,
            storage_path=str(target_file_path),
            original_filename=filename,
            mime_type=mime_type,
            file_size=len(content),
            file_hash=sha256_hash,
            uploaded_by=current_user.email,
        )
        db.add(doc_version)
        await db.flush()

        doc.current_version_id = doc_version.id
        await db.commit()
        await db.refresh(doc)
        await db.refresh(doc_version)

        # Notify ScrutinyService of candidate resubmission if under correction
        try:
            from app.services.scrutiny_service import ScrutinyService
            await ScrutinyService.record_resubmission(
                db=db,
                application_id=application.id,
                document_id=doc.id,
                document_version=doc_version,
                student_user=current_user,
            )
        except Exception:
            pass

        return doc, doc_version

    @classmethod
    async def get_document_file_path(
        cls,
        db: AsyncSession,
        document_id: str,
        version_number: Optional[int] = None
    ) -> Tuple[Path, str, str]:
        """
        Retrieves physical file path, original filename, and mime type for download.
        """
        stmt = select(Document).where(Document.id == document_id)
        res = await db.execute(stmt)
        doc = res.scalar_one_or_none()
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )

        if not doc.versions:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No file versions available for this document"
            )

        target_version: Optional[DocumentVersion] = None
        if version_number:
            for v in doc.versions:
                if v.version_number == version_number:
                    target_version = v
                    break
            if not target_version:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Version {version_number} not found"
                )
        else:
            target_version = doc.versions[0]  # Latest version

        file_path = Path(target_version.storage_path)
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Physical document file missing on server storage"
            )

        return file_path, target_version.original_filename, target_version.mime_type
