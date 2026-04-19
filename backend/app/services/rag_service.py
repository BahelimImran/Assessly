import requests
from typing import List
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

from app.core.config import *
from app.db.chroma_client import collection


# ---------------- EMBEDDING ----------------
def get_embedding(text: str) -> List[float]:
    response = requests.post(
        f"{OLLAMA_BASE_URL}/api/embeddings",
        json={"model": EMBED_MODEL, "prompt": text},
        timeout=120
    )
    data = response.json()
    return data.get("embedding") or data.get("embeddings", [[]])[0]


# ---------------- INGEST ----------------
def ingest_document(pdf_path: str):
    loader = PyPDFLoader(pdf_path)
    documents = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )

    chunks = splitter.split_documents(documents)

    texts, embeddings, metadatas = [], [], []

    for i, chunk in enumerate(chunks):
        emb = get_embedding(chunk.page_content)

        if not emb:
            continue

        texts.append(chunk.page_content)
        embeddings.append(emb)
        metadatas.append(chunk.metadata)

    collection.add(
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas,
        ids=[f"doc_{i}" for i in range(len(texts))]
    )

    return {"chunks": len(texts)}


# ---------------- RETRIEVE ----------------
def get_relevant_chunks(question: str):
    emb = get_embedding(question)

    results = collection.query(
        query_embeddings=[emb],
        n_results=TOP_K
    )

    return results["documents"][0]


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
        json={"model": LLM_PRIMARY, "prompt": prompt, "stream": False},
        timeout=120
    )
    return response.json().get("response", "")


# ---------------- MAIN PIPELINE ----------------
def generate_answer(question: str):
    chunks = get_relevant_chunks(question)

    if not chunks:
        return "No relevant content found."

    context = build_context(chunks)
    prompt = create_prompt(question, context)

    return call_llm(prompt)