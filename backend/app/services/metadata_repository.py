from datetime import datetime, timezone

from sqlalchemy import select

from app.db.postgres import session_scope
from app.models.metadata_models import AuditEvent, Document, IngestionJob, UploadSession, User


def utc_now():
    return datetime.now(timezone.utc)


def ensure_user(external_id: str) -> User:
    with session_scope() as session:
        user = session.scalar(select(User).where(User.external_id == external_id))
        if not user:
            user = User(external_id=external_id)
            session.add(user)
            session.flush()

        session.expunge(user)
        return user


def prepare_upload_metadata(
    *,
    external_user_id: str,
    document_hash: str,
    original_file_name: str,
    stored_file_name: str,
    redis_job_id: str,
) -> dict:
    now = utc_now()

    with session_scope() as session:
        user = session.scalar(select(User).where(User.external_id == external_user_id))
        if not user:
            user = User(external_id=external_user_id)
            session.add(user)
            session.flush()

        document = session.scalar(
            select(Document).where(
                Document.user_id == user.id,
                Document.document_hash == document_hash,
                Document.deleted_at.is_(None),
            )
        )

        if not document:
            document = Document(
                user_id=user.id,
                document_hash=document_hash,
                file_name=original_file_name,
                source_file=stored_file_name,
                status="queued",
            )
            session.add(document)
            session.flush()
        else:
            document.file_name = original_file_name
            document.source_file = stored_file_name
            if not document.active_upload_session_id:
                document.status = "queued"
            document.updated_at = now

        upload_session = UploadSession(
            user_id=user.id,
            document_id=document.id,
            redis_job_id=redis_job_id,
            original_file_name=original_file_name,
            stored_file_name=stored_file_name,
            status="queued",
        )
        session.add(upload_session)
        session.flush()

        ingestion_job = IngestionJob(
            redis_job_id=redis_job_id,
            user_id=user.id,
            document_id=document.id,
            upload_session_id=upload_session.id,
            status="queued",
            progress=0,
            current_step="queued",
        )
        session.add(ingestion_job)

        session.add(
            AuditEvent(
                user_id=user.id,
                document_id=document.id,
                job_id=redis_job_id,
                event_type="document_upload_queued",
                metadata_json={
                    "document_hash": document_hash,
                    "file_name": original_file_name,
                    "stored_file_name": stored_file_name,
                },
            )
        )

        return {
            "user_pk": user.id,
            "document_id": document.id,
            "document_hash": document.document_hash,
            "upload_session_id": upload_session.id,
            "previous_active_upload_session_id": document.active_upload_session_id,
            "job_id": redis_job_id,
        }


def get_document_by_hash(external_user_id: str, document_hash: str) -> dict | None:
    with session_scope() as session:
        document = session.scalar(
            select(Document)
            .join(User, Document.user_id == User.id)
            .where(
                User.external_id == external_user_id,
                Document.document_hash == document_hash,
                Document.deleted_at.is_(None),
            )
        )

        if not document:
            return None

        return {
            "document_id": document.id,
            "document_hash": document.document_hash,
            "file_name": document.file_name,
            "source_file": document.source_file,
            "active_upload_session_id": document.active_upload_session_id,
            "status": document.status,
            "chunk_count": document.chunk_count,
        }


def list_user_documents(external_user_id: str, ready_only: bool = True) -> list[dict]:
    with session_scope() as session:
        filters = [
            User.external_id == external_user_id,
            Document.deleted_at.is_(None),
        ]

        if ready_only:
            filters.append(Document.status == "ready")

        documents = session.scalars(
            select(Document)
            .join(User, Document.user_id == User.id)
            .where(*filters)
            .order_by(Document.updated_at.desc())
        ).all()

        return [
            {
                "document_id": document.id,
                "document_hash": document.document_hash,
                "source_file": document.file_name,
                "status": document.status,
                "chunk_count": document.chunk_count,
                "active_upload_session_id": document.active_upload_session_id,
                "updated_at": document.updated_at.isoformat() if document.updated_at else None,
            }
            for document in documents
        ]


def get_active_upload_session_ids(external_user_id: str, document_id: str | None = None) -> list[str]:
    with session_scope() as session:
        filters = [
            User.external_id == external_user_id,
            Document.deleted_at.is_(None),
            Document.status == "ready",
            Document.active_upload_session_id.is_not(None),
        ]

        if document_id:
            filters.append(Document.id == document_id)

        session_ids = session.scalars(
            select(Document.active_upload_session_id)
            .join(User, Document.user_id == User.id)
            .where(*filters)
        ).all()

        return [session_id for session_id in session_ids if session_id]


def get_document_owner_external_id(document_id: str) -> str | None:
    with session_scope() as session:
        user_external_id = session.scalar(
            select(User.external_id)
            .join(Document, Document.user_id == User.id)
            .where(
                Document.id == document_id,
                Document.deleted_at.is_(None),
            )
        )

        return user_external_id

""" 
Returns non-deleted document IDs.
Used by cleanup logic to detect Qdrant points that no longer have a valid Postgres document.
"""
def list_active_document_ids() -> set[str]:
    with session_scope() as session:
        document_ids = session.scalars(
            select(Document.id).where(Document.deleted_at.is_(None))
        ).all()

        return set(document_ids)

""" 
Returns file names that are referenced by upload sessions.
Used by cleanup logic to detect uploaded files on disk that are not referenced in Postgres. 
"""
def list_referenced_upload_file_names() -> set[str]:
    with session_scope() as session:
        file_names = session.scalars(
            select(UploadSession.stored_file_name)
        ).all()

        return {file_name for file_name in file_names if file_name}

""" 
When worker starts processing, this updates:

ingestion job: processing
document: processing
upload session: processing
audit event: ingestion_started

Postgres keeps durable state, Redis keeps live state.
"""
def mark_ingestion_started(redis_job_id: str, attempt_count: int):
    with session_scope() as session:
        job = session.scalar(select(IngestionJob).where(IngestionJob.redis_job_id == redis_job_id))
        if not job:
            return

        job.status = "processing"
        job.progress = 10
        job.current_step = "processing"
        job.attempt_count = attempt_count
        job.error = None
        job.started_at = job.started_at or utc_now()

        if not job.document.active_upload_session_id:
            job.document.status = "processing"

        upload_session = session.get(UploadSession, job.upload_session_id)
        if upload_session:
            upload_session.status = "processing"

        session.add(
            AuditEvent(
                user_id=job.user_id,
                document_id=job.document_id,
                job_id=redis_job_id,
                event_type="ingestion_started",
                metadata_json={"attempt_count": attempt_count},
            )
        )

""" 
Updates durable job progress in Postgres.
If Redis expires or restarts, Postgres still has progress history.
 """
def update_ingestion_progress(redis_job_id: str, current_step: str, progress: int):
    with session_scope() as session:
        job = session.scalar(select(IngestionJob).where(IngestionJob.redis_job_id == redis_job_id))
        if not job:
            return

        job.current_step = current_step
        job.progress = progress

""" 
When worker completes ingestion, this updates:

job: completed
document: ready
document chunk count
upload session: completed
audit event: ingestion_completed

Knowledge base only shows ready documents.
 """
def mark_ingestion_completed(redis_job_id: str, chunk_count: int):
    now = utc_now()

    with session_scope() as session:
        job = session.scalar(select(IngestionJob).where(IngestionJob.redis_job_id == redis_job_id))
        if not job:
            return

        job.status = "completed"
        job.progress = 100
        job.current_step = "completed"
        job.error = None
        job.completed_at = now

        document = job.document
        document.status = "ready"
        document.chunk_count = chunk_count
        document.active_upload_session_id = job.upload_session_id
        document.updated_at = now

        upload_session = session.get(UploadSession, job.upload_session_id)
        if upload_session:
            upload_session.status = "completed"
            upload_session.completed_at = now
            upload_session.error = None

        session.add(
            AuditEvent(
                user_id=job.user_id,
                document_id=job.document_id,
                job_id=redis_job_id,
                event_type="ingestion_completed",
                metadata_json={"chunk_count": chunk_count},
            )
        )

""" 
When worker fails ingestion, this updates:

job: failed
document: failed
upload session: failed
error message
audit event: ingestion_failed

Failed documents should not appear as searchable knowledge.
 """
def mark_ingestion_failed(redis_job_id: str, error: str):
    now = utc_now()

    with session_scope() as session:
        job = session.scalar(select(IngestionJob).where(IngestionJob.redis_job_id == redis_job_id))
        if not job:
            return

        job.status = "failed"
        job.progress = 0
        job.current_step = "failed"
        job.error = error
        job.failed_at = now

        if not job.document.active_upload_session_id:
            job.document.status = "failed"

        upload_session = session.get(UploadSession, job.upload_session_id)
        if upload_session:
            upload_session.status = "failed"
            upload_session.failed_at = now
            upload_session.error = error

        session.add(
            AuditEvent(
                user_id=job.user_id,
                document_id=job.document_id,
                job_id=redis_job_id,
                event_type="ingestion_failed",
                metadata_json={"error": error},
            )
        )


def mark_document_deleted(document_id: str, external_user_id: str) -> dict | None:
    now = utc_now()

    with session_scope() as session:
        document = session.scalar(
            select(Document)
            .join(User, Document.user_id == User.id)
            .where(
                Document.id == document_id,
                User.external_id == external_user_id,
                Document.deleted_at.is_(None),
            )
        )

        if not document:
            return None

        document.status = "deleted"
        document.deleted_at = now
        document.updated_at = now

        session.add(
            AuditEvent(
                user_id=document.user_id,
                document_id=document.id,
                event_type="document_deleted",
                metadata_json={
                    "document_hash": document.document_hash,
                    "active_upload_session_id": document.active_upload_session_id,
                },
            )
        )

        return {
            "document_id": document.id,
            "document_hash": document.document_hash,
            "active_upload_session_id": document.active_upload_session_id,
        }
