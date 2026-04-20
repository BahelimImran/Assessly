from fastapi import APIRouter
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
        return {"error":str(e)}