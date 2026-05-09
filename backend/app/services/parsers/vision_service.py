import base64
import requests
from dotenv import load_dotenv; load_dotenv()
import os; 
VISION_MODEL = os.getenv("VISION_MODEL")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")

# OLLAMA_BASE_URL = "http://localhost:11434"
# VISION_MODEL = "qwen2.5vl:3b"


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