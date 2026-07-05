from uuid import UUID

from fastapi import APIRouter, Depends, File, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.documents.schemas import DocumentRead, DocumentUploadRead
from app.documents.service import (
    create_document_from_upload,
    delete_user_document,
    document_to_read,
    document_to_upload_read,
    get_document_summary_status,
    get_user_document,
    list_user_documents,
)
from app.users.models import User


router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentUploadRead, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> DocumentUploadRead:
    document = await create_document_from_upload(db, current_user, file, settings)
    return document_to_upload_read(document)


@router.get("", response_model=list[DocumentRead])
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[DocumentRead]:
    return [
        document_to_read(document, get_document_summary_status(db, document))
        for document in list_user_documents(db, current_user)
    ]


@router.get("/{document_id}", response_model=DocumentRead)
def get_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentRead:
    document = get_user_document(db, current_user, document_id)
    return document_to_read(document, get_document_summary_status(db, document))


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    delete_user_document(db, current_user, document_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
