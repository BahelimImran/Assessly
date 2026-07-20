
import json
import logging
from typing import Dict
from app.core.config import *
from app.services.model_client import ModelCallError, ModelCallTimeout, post_json_with_retry
import re
from app.services.dataset.dataset_service import create_dataset_entry


logger = logging.getLogger(__name__)

def generate_questions_for_chunk(parent_chunk):
    logger = logging.getLogger(__name__)

    full_text = parent_chunk.payload["full_text"]

    prompt = f"""
    Generate exactly 3 realistic user questions from the given content.

    Content:
    {full_text}

    Return JSON:
    [
      {{"question": "..."}},
      {{"question": "..."}},
      {{"question": "..."}}
    ]
    """
    try:
        logger.info("Dataset generation started")
        final_prompt = "" + prompt
        data = post_json_with_retry(
            f"{OLLAMA_BASE_URL}/api/generate",
            {
                "model": LLM_MODEL,
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


        questions = parse_llm_json(data['response'])
        logger.info("Dataset question find LLM inference completed")
        # Task - Move data create to dataset.py and need to remove records of same document ingested again after successfull ingestion 
        for q in questions:
            create_dataset_entry(
                username=parent_chunk.payload["user_id"],
                question=q["question"],
                ground_truth_chunk_ids=parent_chunk.payload["parent_id"],
                document_id=parent_chunk.payload["document_id"],
                metadata_info=parent_chunk.payload,
            )
        
        return questions 
        
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