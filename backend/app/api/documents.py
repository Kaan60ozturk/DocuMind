"""Document endpoints: upload, list, delete."""

import logging
import re
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, UploadFile

from app.core.ingestion import EmptyDocumentError, ingest_file
from app.core.parsing import SUPPORTED_EXTENSIONS, ParsingError
from app.providers.base import ProviderError
from app.schemas import DocumentOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/documents", tags=["documents"])

_UNSAFE_CHARS = re.compile(r"[\x00-\x1f\x7f<>]")
_MAX_DISPLAY_NAME = 255


def _sanitize_display_name(raw: str | None) -> str:
    """Keep only the base name, drop control characters, cap the length."""
    name = Path(raw or "upload").name
    name = _UNSAFE_CHARS.sub("", name).strip()
    return name[:_MAX_DISPLAY_NAME] or "upload"


@router.post("", status_code=201, response_model=DocumentOut)
def upload_document(request: Request, file: UploadFile) -> DocumentOut:
    state = request.app.state
    settings = state.settings

    display_name = _sanitize_display_name(file.filename)
    extension = Path(display_name).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{extension or 'none'}'. Supported: {supported}.",
        )

    contents = file.file.read()
    if len(contents) > settings.max_file_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File is too large. The limit is {settings.max_file_mb} MB.",
        )
    if not contents:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    doc_id = str(uuid.uuid4())
    stored_path = settings.uploads_dir / f"{doc_id}{extension}"
    stored_path.write_bytes(contents)

    try:
        record = ingest_file(
            stored_path,
            display_name,
            settings=settings,
            embedder=state.embedder,
            vectorstore=state.vectorstore,
            registry=state.registry,
            doc_id=doc_id,
        )
    except (ParsingError, EmptyDocumentError) as exc:
        stored_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ProviderError as exc:
        stored_path.unlink(missing_ok=True)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception:
        stored_path.unlink(missing_ok=True)
        logger.exception("Unexpected error while ingesting %r", display_name)
        raise HTTPException(
            status_code=500, detail="Something went wrong while processing the document."
        ) from None

    return DocumentOut.model_validate(record)


@router.get("", response_model=list[DocumentOut])
def list_documents(request: Request) -> list[DocumentOut]:
    return [DocumentOut.model_validate(record) for record in request.app.state.registry.list()]


@router.delete("/{doc_id}", status_code=204)
def delete_document(request: Request, doc_id: str) -> None:
    state = request.app.state
    if state.registry.get(doc_id) is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    state.vectorstore.delete_document(doc_id)
    for stored_file in state.settings.uploads_dir.glob(f"{doc_id}.*"):
        stored_file.unlink(missing_ok=True)
    state.registry.delete(doc_id)
    logger.info("Deleted document %s", doc_id)
