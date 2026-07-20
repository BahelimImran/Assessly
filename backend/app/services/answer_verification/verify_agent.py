
import json
import logging
from typing import Dict
from app.core.config import *
from app.services.model_client import ModelCallError, ModelCallTimeout, post_json_with_retry
import re


# from app.services.rag_service import call_llm

logger = logging.getLogger(__name__)

def verify_answer(
    answer: str,
    context: str,
    query: str
) -> Dict:
    logger = logging.getLogger(__name__)

    prompt = f"""
        You are a strict AI evaluator.

        Question:
        {query}

        Context:
        {context}

        Answer:
        {answer}

        Evaluate strictly:
        1. Is the answer grounded in the context?
        2. Any hallucinations or unsupported claims?
        3. Is the answer complete?

        Return ONLY JSON:
        {{
        "passed": true or false,
        "score": 0.0 to 1.0,
        "reason": "short explanation"
        }}
        """
    try:
        logger.info("Verify agent started")
        final_prompt = "" + prompt
        data = post_json_with_retry(
            f"{OLLAMA_BASE_URL}/api/generate",
            {
                "model": ANSWER_VERIFICATION_LLM_MODEL,
                "prompt": final_prompt,
                "stream": False,
                "keep_alive":0 ,
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
        # result = json.loads(data['response'])
        logger.info("Verify agent find LLM inference completed")
        
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