from app.services.query_intension_router.query_router_service import rule_based_router
from app.services.query_intension_router.llm_router import llm_router


def hybrid_router(query: str):
    rule = rule_based_router(query)

    if rule["confidence"] >= 0.8:
        return rule

    llm = llm_router(query)
    print(f"llm result:{llm}")

    if llm["confidence"] < 0.6:
        return {"route": "RAG", "confidence": 0.5, "reason": "fallback_default"}

    return llm