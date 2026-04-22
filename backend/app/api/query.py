from fastapi import APIRouter, HTTPException
from app.models.schema import QueryRequest
from app.services.rag_service import generate_answer

router = APIRouter()


@router.post("/")
def query(req: QueryRequest):
    try:
        answer = generate_answer(req.question)
        return {
            "question": req.question,
            "answer": answer
        }
    except Exception as e:
        print("Query error:", str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Query failed: {str(e)}"
        )

