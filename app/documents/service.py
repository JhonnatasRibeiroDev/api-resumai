import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings
from app.documents.models import Document
from app.documents.schemas import DocumentRead, DocumentUploadRead
from app.users.models import User
from app.utils.pdf import PDFExtractionError, extract_text_from_pdf


ACCEPTED_PDF_MIME_TYPES = {"application/pdf", "application/x-pdf"}
UPLOAD_CHUNK_SIZE = 1024 * 1024


def document_to_read(document: Document) -> DocumentRead:
    return DocumentRead(
        id=document.id,
        filename=document.filename,
        file_size=document.file_size,
        mime_type=document.mime_type,
        created_at=document.created_at,
        summary_status="completed" if document.summary else "pending",
    )


def document_to_upload_read(document: Document) -> DocumentUploadRead:
    return DocumentUploadRead(**document_to_read(document).model_dump())


def _validate_pdf_metadata(file: UploadFile) -> str:
    filename = Path(file.filename or "").name
    if not filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo sem nome.",
        )

    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Apenas arquivos .pdf são aceitos.",
        )

    if file.content_type not in ACCEPTED_PDF_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="MIME type inválido. Envie um PDF.",
        )

    return filename


async def _save_upload_file(
    file: UploadFile,
    destination: Path,
    max_size_bytes: int,
) -> int:
    bytes_written = 0
    destination.parent.mkdir(parents=True, exist_ok=True)

    with destination.open("wb") as buffer:
        while chunk := await file.read(UPLOAD_CHUNK_SIZE):
            bytes_written += len(chunk)
            if bytes_written > max_size_bytes:
                destination.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="Arquivo excede o limite de upload.",
                )
            buffer.write(chunk)

    if bytes_written == 0:
        destination.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="PDF vazio.",
        )

    return bytes_written


async def create_document_from_upload(
    db: Session,
    user: User,
    file: UploadFile,
    settings: Settings,
) -> Document:
    filename = _validate_pdf_metadata(file)
    document_id = uuid.uuid4()
    storage_path = Path(settings.upload_dir) / str(user.id) / f"{document_id}.pdf"

    file_size = await _save_upload_file(
        file=file,
        destination=storage_path,
        max_size_bytes=settings.max_upload_size_bytes,
    )

    try:
        extracted_text = extract_text_from_pdf(storage_path)
    except PDFExtractionError as exc:
        storage_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    document = Document(
        id=document_id,
        user_id=user.id,
        filename=filename,
        file_path=str(storage_path),
        file_size=file_size,
        mime_type=file.content_type or "application/pdf",
        extracted_text=extracted_text,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def list_user_documents(db: Session, user: User) -> list[Document]:
    return list(
        db.scalars(
            select(Document)
            .options(selectinload(Document.summary))
            .where(Document.user_id == user.id)
            .order_by(Document.created_at.desc())
        )
    )


def get_user_document(db: Session, user: User, document_id: uuid.UUID) -> Document:
    document = db.scalar(
        select(Document)
        .options(selectinload(Document.summary))
        .where(Document.id == document_id, Document.user_id == user.id)
    )
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento não encontrado.",
        )
    return document


def delete_user_document(db: Session, user: User, document_id: uuid.UUID) -> None:
    document = get_user_document(db, user, document_id)
    file_path = Path(document.file_path)

    db.delete(document)
    db.commit()
    file_path.unlink(missing_ok=True)
