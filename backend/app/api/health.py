from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.db.postgres import engine
from app.db.qdrant_client import qdrant
from app.services.redis_client import redis_client


router = APIRouter()


@router.get("/redis")
def redis_health():
    try:
        redis_client.ping()
        return {"status": "ok"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Redis unhealthy: {str(exc)}")


@router.get("/qdrant")
def qdrant_health():
    try:
        qdrant.get_collections()
        return {"status": "ok"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Qdrant unhealthy: {str(exc)}")


@router.get("/postgres")
def postgres_health():
    try:
        with engine.connect() as connection:
            connection.execute(text("select 1"))
        return {"status": "ok"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Postgres unhealthy: {str(exc)}")
