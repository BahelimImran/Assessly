from sqlalchemy import func, select

from fastapi import APIRouter, Depends

from app.db.postgres import session_scope
from app.models.metadata_models import Document, IngestionJob, User
from app.services.auth_dependencies import AuthPrincipal, require_admin


router = APIRouter()


@router.get("/health")
def admin_health(_: AuthPrincipal = Depends(require_admin)):
    with session_scope() as session:
        return {
            "status": "ok",
            "users": session.scalar(select(func.count()).select_from(User)),
            "documents": session.scalar(select(func.count()).select_from(Document)),
            "failed_jobs": session.scalar(
                select(func.count()).select_from(IngestionJob).where(IngestionJob.status == "failed")
            ),
        }


@router.get("/users")
def list_users(_: AuthPrincipal = Depends(require_admin)):
    with session_scope() as session:
        users = session.scalars(select(User).order_by(User.created_at.desc())).all()
        return {
            "users": [
                {
                    "user_id": user.external_id,
                    "email": user.email,
                    "role": user.role,
                    "is_active": bool(user.is_active),
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                }
                for user in users
            ]
        }


@router.get("/jobs/failed")
def list_failed_jobs(_: AuthPrincipal = Depends(require_admin)):
    with session_scope() as session:
        jobs = session.scalars(
            select(IngestionJob)
            .where(IngestionJob.status == "failed")
            .order_by(IngestionJob.failed_at.desc())
            .limit(100)
        ).all()
        return {
            "jobs": [
                {
                    "redis_job_id": job.redis_job_id,
                    "user_id": job.user_id,
                    "document_id": job.document_id,
                    "error": job.error,
                    "failed_at": job.failed_at.isoformat() if job.failed_at else None,
                }
                for job in jobs
            ]
        }
