
import json
import asyncio
from app.services.dataset.dataset_generate import generate_questions_for_chunk
import logging
from typing import Dict
from app.core.config import *

logger = logging.getLogger(__name__)

def generate_dataset_from_parent_chunks(parent_chunks, batch_size=10):
    """
    Generate 3 questions per parent chunk and store in DB
    """
    try:
        dataset = []
        for i in range(0, len(parent_chunks), batch_size):
            batch = parent_chunks[i:i + batch_size]
            for chunk in batch:
                questions = generate_questions_for_chunk(chunk)
    except Exception as error:
        logger.exception("Unexpected dataset prepare LLM error")
        return "The local AI model failed unexpectedly. Please try again."





