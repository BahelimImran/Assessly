import requests
from typing import List

from app.core.config import *
from app.db.chroma_client import collection

from app.services.pdf_parser import parse_pdf
from app.services.element_processor import process_elements
from langchain.text_splitter import RecursiveCharacterTextSplitter
import numpy as np



# ---------------- EMBEDDING ----------------
def get_embedding(text: str) -> List[float]:
    response = requests.post(
        f"{OLLAMA_BASE_URL}/api/embeddings",
        json={"model": EMBED_MODEL, "prompt": text},
        timeout=120
    )
    data = response.json()
    return data.get("embedding") or data.get("embeddings", [[]])[0]


def cosine_similarity(emb1: List[float], emb2: List[float]) -> float:
    a = np.array(emb1)
    b = np.array(emb2)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


# ---------------- INGEST ----------------

def ingest_pdf(file_path):
    # parse pdf
    elements = parse_pdf(file_path) 

    # process elements
    docs, metas = process_elements(elements, file_path)

    # chunking only for large text
    splitter = RecursiveCharacterTextSplitter(
        chunk_size = 500,
        chunk_overlap = 50
    )

    final_docs = []
    final_metas = []

    for doc, meta in zip(docs, metas): 
        chunks = splitter.split_text(doc)

        for chunk in chunks:
            final_docs.append(chunk)
            final_metas.append(meta)
    
    # Embeddings ??
    embeddings = []
    for text in final_docs:
        emb = get_embedding(text)

        if emb:
            embeddings.append(emb)
        else:
            embeddings.append([0.0] * 786) # fallback 

    # Store in Chroma
    ids = [f"{file_path}_{i}" for i in range(len(final_docs))]
    collection.add(
        documents = final_docs,
        metadatas = final_metas,
        embeddings = embeddings,
        ids=ids 
    )
    return {"chunks ": len(final_docs)}


# ---------------- RETRIEVE ----------------
def get_relevant_chunks(question: str):
    
    emb = get_embedding(question)

    results = collection.query(
        query_embeddings=[emb],
        n_results=TOP_K
    )
    
    return results["documents"][0]

def query_rag(query):
    emb = get_embedding(query)

    results = collection.query(
        query_embeddings=[emb],
        n_results = 5,
        include=["documents", "metadatas", "embeddings"]
    )
    docs = results["documents"][0]
    metas = results["metadatas"][0]
    doc_embeddings = results["embeddings"][0]

    response = []
    """
    docs, metas, and doc_embeddings are three parallel lists
    zip(...) iterates over them together
    each loop gets one doc, one matching meta, and one matching doc_emb
    the loop stops when the shortest list runs out
    """
    for doc, meta, doc_emb in zip(docs, metas, doc_embeddings):
        similarity = cosine_similarity(emb, doc_emb)
        passes_test = similarity > 0.8  # Threshold for "passes test"
        response.append({
            "content": doc,
            "page": meta.get("page"),
            "type": meta.get("type"),
            "similarity": round(similarity, 4),
            "passes_similarity_test": passes_test
        })
    final_result = []
    for content in response:
        final_result.append(content["content"])

    return final_result 

# ---------------- PROMPT ----------------
def build_context(chunks: List[str]) -> str:
    return "\n".join(chunks)


def create_prompt(question: str, context: str):
    return f"""
You are a helpful AI tutor.

ONLY use the context below.
If not found, say "Not found in document".

Context:
{context}

Question:
{question}
"""


# ---------------- LLM ----------------
def call_llm(prompt: str):
    response = requests.post(
        f"{OLLAMA_BASE_URL}/api/generate",
        json={"model": LLM_MODEL, "prompt": prompt, "stream": False},
        timeout=120
    )
    return response.json().get("response", "")


# ---------------- MAIN PIPELINE ----------------
def generate_answer(question: str):
    chunks = query_rag(question)

    if not chunks:
        return "No relevant content found."

    context = build_context(chunks)
    prompt = create_prompt(question, context)

    return call_llm(prompt)