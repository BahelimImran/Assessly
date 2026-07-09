import json
import logging
from app.services.model_client import post_json_with_retry
from app.core.config import *
from app.services.model_client import ModelCallError, ModelCallTimeout, post_json_with_retry
import re


def llm_router(query: str):
    logger = logging.getLogger(__name__)

    prompt = f"""
        You are a classifier for a wireline oilfield AI system.

        Classify:
        - RAG → needs oilfield/wireline/job/procedure knowledge
        - NO_RAG → math, general knowledge, greetings, writing

        Return JSON:
        {{
        "route": "RAG" or "NO_RAG",
        "confidence": 0-1,
        "reason": "short reason"
        }}

        Query: {query}
        """
    try:
        logger.info("Query intension find LLM inference started", extra={"prompt_length": len(prompt)})
        final_prompt = "/no_think\n\n" + prompt
        data = post_json_with_retry(
            f"{OLLAMA_BASE_URL}/api/generate",
            {
                "model": QUERY_ROUTER_LLM_MODEL,
                "prompt": final_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.0,
                    "num_ctx": 8096,
                    "num_predict": 850
                }
            },
            timeout=LLM_REQUEST_TIMEOUT_SECONDS,
            request_name="ollama_generation"
        )


        result = parse_llm_json(data['response'])
        logger.info("Query intension find LLM inference completed")
        
        return result #.get("response", "").strip()
        
    except ModelCallTimeout:
        return "The local AI model took too long to respond. Please try with a shorter question or smaller document context."
    except ModelCallError as e:
        logger.warning("LLM call failed", extra={"error": str(e)})
        return "The local AI model is temporarily unavailable. Please try again."
    except Exception:
        logger.exception("Unexpected LLM error")
        return "The local AI model failed unexpectedly. Please try again."

def parse_llm_json(raw: str):
    # Remove markdown wrapper
    cleaned = re.sub(r"```json|```", "", raw).strip()
    
    # Load JSON
    return json.loads(cleaned)