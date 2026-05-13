import base64
import requests
from dotenv import load_dotenv; load_dotenv()
import os; 
from pathlib import Path
from typing import List, Dict, Any
VISION_MODEL = os.getenv("VISION_MODEL")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")

# OLLAMA_BASE_URL = "http://localhost:11434"
# VISION_MODEL = "qwen2.5vl:3b"

# Qwen2.5-VL can handle:

# text
# OCR/scanned pages
# tables
# charts/graphs
# diagrams
# figures
# forms
# handwriting
# screenshots
# equations/math
# mixed-layout documents

def image_to_base64(image_path: str) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def call_ollama_vision(image_path: str, prompt: str) -> str:
    try:
        image_base64 = image_to_base64(image_path)

        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": VISION_MODEL,
                "prompt": prompt,
                "images": [image_base64],
                "stream": False,
                "options": {
                    "temperature": 0.2,
                    "num_ctx": 4096,
                    "num_predict": 300
                }
            },
            timeout=180
        )

        response.raise_for_status()

        data = response.json()

        return data.get("response", "").strip()

    except Exception as e:
        print(f"Vision model error: {e}")
        return ""
    
def enrich_visual_elements(elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    enriched_elements = []

    for element in elements:
        if element.get("type") not in ["image"]:
            enriched_elements.append(element)
            continue

        image_path = element.get("image_path")

        if not image_path or not Path(image_path).exists():
            enriched_elements.append(element)
            continue

        try:
            image_summary = summarize_image_with_vision_model(image_path)
        except Exception as e:
            print(f"Vision enrichment skipped for {image_path}: {e}")
            image_summary = ""

        element["image_summary"] = image_summary

        element["retrieval_text"] = "\n".join([
            element.get("image_caption", ""),
            element.get("ocr_text", ""),
            element.get("image_summary", "")
        ]).strip()

        element["metadata"]["content_type"] = detect_visual_type(image_summary)

        enriched_elements.append(element)

    return enriched_elements

def summarize_image_with_vision_model(image_path: str) -> str:
    try:
        image_base64 = encode_image_to_base64(image_path)

        prompt = """
                You are analyzing an image extracted from a PDF document.

                Describe the image for a RAG knowledge assistant.

                Return a concise but useful summary covering:
                1. What the image/chart/diagram shows
                2. Any visible text
                3. Important labels, values, trends, stages, or relationships
                4. Why this visual may be useful for answering user questions

                Do not hallucinate. If unclear, say what is unclear.
                """

        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": VISION_MODEL,
                "prompt": prompt,
                "images": [image_base64],
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_predict": 250
                }
            },
            timeout=180
        )

        response.raise_for_status()

        return response.json().get("response", "").strip()

    except Exception as e:
        print(f"Vision enrichment failed for {image_path}: {e}")
        return ""
def encode_image_to_base64(image_path: str) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def detect_visual_type(image_summary: str) -> str:
    text = image_summary.lower()

    chart_keywords = ["chart", "graph", "trend", "axis", "bar", "line", "pie"]
    diagram_keywords = ["diagram", "flow", "process", "architecture", "workflow"]

    if any(keyword in text for keyword in chart_keywords):
        return "chart"

    if any(keyword in text for keyword in diagram_keywords):
        return "diagram"

    return "image"


def summarize_table_basic(table_md: str) -> str:
    lines = [line for line in table_md.splitlines() if line.strip()]
    if not lines:
        return ""

    return f"Table with {len(lines)} rows. Content: {table_md[:500]}"