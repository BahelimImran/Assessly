import os
import logging
from typing import List
from datetime import datetime, timezone

from app.core.config import *
# from app.db.chroma_client import collection
from app.db.qdrant_client import qdrant, create_collections
from qdrant_client.models import PointStruct
from app.db.qdrant_client import get_sparse_model
from app.core.config import PERSIST_DIR, VECTOR_SIZE

# from app.services.pdf_parser import parse_pdf
# from app.services.chunking.chunk_service import process_document
# from app.services.element_processor import process_elements
from langchain.text_splitter import RecursiveCharacterTextSplitter
from app.services.parsers.docling_parser import parse_pdf_with_docling, build_docling_chunks, parse_document
# import numpy as np

from app.services.identify_document.identify_document import hash_file_bytes, hash_text, clean_metadata
# from app.services.retrieval_search.bm25_search import *
from app.services.retrieval_search.child_chunks_retrieval import *
from app.services.retrieval_search.parent_chunks_retrieval import fetch_parent_chunks
from app.services.metadata_repository import get_active_upload_session_ids
from app.services.model_client import ModelCallError, ModelCallTimeout, post_json_with_retry
# from app.services.retrieval_search.merge_vector_bm25 import *
# from app.services.retrieval_search.reranker import *
# from app.services.retrieval_search.context_compressor import *
from app.services.measure_confidence.calculate_confidence import *
import uuid

logger = logging.getLogger(__name__)


# ---------------- INGEST ----------------
def ingest_pdf(file_path, log, user_id, document_id: str | None = None, document_hash: str | None = None, upload_session_id: str | None = None):
    print("\n\n\n 📥 Ingesting document...")
    print(f"\n ⚙️  [File: {file_path}]")
    
    source_file = os.path.basename(file_path)
    document_hash = document_hash or hash_file_bytes(file_path)
    document_id = document_id or document_hash
    created_at = datetime.now(timezone.utc).isoformat()

    upload_session_id = upload_session_id or str(uuid.uuid4())
    user_id = user_id


    # existing = collection.get(
    #     where={"document_id":document_id},
    #     include=["metadatas"]
    # )

    # if existing.get("ids"):
    #     return {
    #         "status": "duplicate",
    #         "message": "This document already exists in knowledge base.",
    #         "document_id": document_id,
    #         "source_file": os.path.basename(file_path),
    #         "chunks": len(existing["ids"])
    #     }

    log(f"✔️ 📄 Parsing document structure...{user_id}")
    print("\n\n\n\n\n 📄 Parsing document structure...")
    print(f"\n ⚙️  [Hi-res parsing + layout detection]")
    
    # # parse pdf
    # elements = parse_pdf(file_path) 

    # all_chunks = process_document(elements, file_path)

    all_chunks = parse_document(file_path, log)

    # final_docs = []
    # final_metas = []
    # ids = []




    # for index, chunk in enumerate(all_chunks["chunks"]): # Todo
    #     # 'searchable_content' is only available for child and not for parent
    #     content = chunk.get("content", "").strip()

    #     if not content:
    #         continue
        
    #     chunk_hash = hash_text(content)
    #     chunk_id = f"{document_id}_{chunk_hash}" # Note- no use yet

    #     metadata = {

    #             # Identity
    #             "document_id": document_id,
    #             "file_name": source_file,
    #             "source_file": source_file,
    #             "upload_session_id": upload_session_id,
    #             "user_id": user_id,

    #             # Location
    #             "page": chunk.get("page_number", chunk.get("page", "")), # Todo - add
    #             "page_number": chunk.get("page_number", chunk.get("page", "")), # Todo - add

    #             # Section
    #             "section": chunk.get("section_title", chunk.get("title", "")),
    #             "section_title": chunk.get("section_title", chunk.get("title", "")),
    #             "section_path": chunk.get("section_path", ""), # important to show - Finance Approval Matrix > 3. Approval Limits > 3.2 Department Head Approval

    #             # Chunk
    #             "chunk_type": chunk.get("chunk_type", "text"), # Note- parant-section and child-text allocated by docling
    #             "chunk_index": index,
    #             "chunk_hash": chunk_hash,

    #             # Useful extras
    #             "total_pages": chunk.get("total_pages", ""), #Note - chunk don't have
    #             "heading_level": chunk.get("heading_level", ""),#Note - chunk don't have
    #             "content_preview": content[:180],
    #             "word_count": len(content.split()),
    #             "char_count": len(content),
    #             "source_type": "pdf",
    #             "parser": chunk.get("parser", "docling"),
    #             "image_path": chunk.get("image_path", ""),
    #             "created_at": created_at,
    #     }
    #     final_docs.append(content)
    #     final_metas.append(clean_metadata(metadata))
    #     ids.append(chunk_id)
    
    
    # embeddings = []
    # log("✔️ 📄 Parsing document structure...")
    # log("✔️ 🧠 Generating embeddings...")
    # log("✔️ 📦 Storing in vector database...")
    # print("\n\n\n\n\n 🧠 Generating embeddings...")
    # print(f"\n ⚙️  [Embedding model: bge-m3]")
    # for text in final_docs:
    #     emb = get_embedding(text)

    #     if not emb:
    #         raise Exception("Embedding generation failed. Empty embedding returned")
        
    #     embeddings.append(emb)
        
    # log("✔️ 📦 Storing in vector database...")
    # print("\n\n\n\n\n 📦 Storing in vector database...")
    # print(f"\n ⚙️  [Qdrantdb updated]")	
    # # Store in Chroma
    # # ids = [f"{file_path}_{i}" for i in range(len(final_docs))]

    # points = []

    # for doc, embedding, metadata, custom_chunk_id in zip(final_docs, embeddings, final_metas, ids):
    #     points.append(
    #         PointStruct(
    #             id=str(uuid.uuid4()),
    #             vector=embedding,
    #             payload={
    #                 "content": doc,
    #                 "chunk_id": custom_chunk_id, 
    #                 **metadata
    #             }
    #         )
    #     )

    # if final_docs:
    #     qdrant.upsert(
    #         collection_name = QDRANT_COLLECTION,
    #         points=points
    #     )

    # parents qdrant points
    parents_points = []

    for parent in all_chunks["parent_chunks"]:

        parent_id = parent.get("parent_id", str(uuid.uuid4()))
        parent["parent_id"] = parent_id

        parent_title = parent.get("title", "")
        parent_content = "\n\n".join(parent.get("content", []))

        full_parent_text = f"{parent_title}\n\n{parent_content}"

        parents_points.append(
            PointStruct(
                id=parent_id,
                vector={},
                payload={
                    "parent_id": parent_id,
                    "document_id": document_id,
                    "document_hash": document_hash,
                    "user_id": user_id,
                    "upload_session_id": upload_session_id,
                    "source_file":source_file,
                    "section_title": parent_title,
                    "full_text": full_parent_text,
                    "content": parent.get("content", []),
                    "content_type": "parent_section"
                }
            )
        )

    
    # # childs qdrant points
    # childs_points = []

    # # Embedding in-progress
    # log("✔️ 🧠 Generating dense(semantics) and parse(keywords) embeddings...")
    # for child in all_chunks["child_chunks"]:

    #     child_id = child.get("child_id") or str(uuid.uuid4())
    #     child["child_id"] = child_id

    #     text_for_embedding = child.get("chunk_text", "")
    #     embedding = get_embedding(text_for_embedding) # Todo-later change with batch embedding - Huge speed improvement
    #     sparse_embedding = list(sparse_model.embed([text_for_embedding]))[0]

    #     childs_points.append(
    #         PointStruct(
    #             id=child_id,
    #             # vector=embedding,
    #             vector={
    #                 "dense": embedding,
    #                 "sparse": {
    #                     "indices": sparse_embedding.indices.tolist(),
    #                     "values": sparse_embedding.values.tolist()
    #                 }
    #             },
    #             payload={
    #                 "user_id": user_id or "default_user",
    #                 "child_id": child_id,
    #                 "parent_id": child.get("parent_id"),
    #                 "document_id": document_id,
    #                 "section_title": child.get("section_title", ""),
    #                 "chunk_text": text_for_embedding,
    #                 "chunk_type": child.get("chunk_type", "paragraph"),
    #                 "content_type": "child_chunk"
    #             }
    #         )
    #     )
    
    child_chunks = [
        child for child in all_chunks["child_chunks"]
        if child.get("chunk_text", "").strip()
    ]

    texts = [child["chunk_text"] for child in child_chunks]

    log(f"✔️ 🧠 Generating batch embeddings for {len(texts)} child chunks...")

    dense_embeddings = get_embeddings_batch(texts)

    sparse_embeddings = list(get_sparse_model().embed(texts))

    childs_points = []

    for child, dense_embedding, sparse_embedding in zip(
        child_chunks,
        dense_embeddings,
        sparse_embeddings
    ):
        child_id = child.get("child_id") or str(uuid.uuid4())
        child["child_id"] = child_id

        text_for_embedding = child.get("chunk_text", "")

        childs_points.append(
            PointStruct(
                id=child_id,
                vector={
                    "dense": dense_embedding,
                    "sparse": {
                        "indices": sparse_embedding.indices.tolist(),
                        "values": sparse_embedding.values.tolist()
                    }
                },
                payload={
                    "user_id": user_id,
                    "child_id": child_id,
                    "parent_id": child.get("parent_id"),
                    "document_id": document_id,
                    "document_hash": document_hash,
                    "upload_session_id": upload_session_id,
                    "source_file":source_file,
                    "section_title": child.get("section_title", ""),
                    "chunk_text": text_for_embedding,
                    "chunk_type": child.get("chunk_type", "paragraph"),
                    "content_type": "child_chunk"
                }
            )
        )
            

    # qdrant store
    log(f"✔️ 📦 Storing vectors(parents, childs) in database...{user_id}")
    create_collections()

    # qdrant.upsert(
    #     collection_name=PARENT_COLLECTION,
    #     points=parents_points
    # )
    for batch in batched(parents_points, batch_size=64):
        qdrant.upsert(
            collection_name=PARENT_COLLECTION,
            points=batch
        )    

    # qdrant.upsert(
    #     collection_name=CHILD_COLLECTION,
    #     points=childs_points
    # )
    for batch in batched(childs_points, batch_size=64):
        qdrant.upsert(
            collection_name=CHILD_COLLECTION,
            points=batch
        )

    log(f"✔️ ✅ Ingestion complete...{user_id}")
    print("\n\n\n\n\n ✅ Ingestion complete")
    print(f"\n ⚙️  [Total ingested chunks: {len(childs_points)} | Status: Success]\n\n\n")	
    print("=================================================================================")
    log(f"✅ All set! You can start asking questions now.")
    return {
        "document_id": document_id,
        "document_hash": document_hash,
        "file_name": source_file,
        "source_file": source_file,
        "upload_session_id": upload_session_id,
        "user_id": user_id,
        "chunks": len(childs_points),
        "replaced_existing_chunks": {}
    }

def batched(items, batch_size=64):
    for i in range(0, len(items), batch_size):
        yield items[i:i + batch_size]
# ---------------- EMBEDDING ----------------
def get_embedding(text: str) -> List[float]:
    
    if EMBED_PROVIDER == "ollama":

        data = post_json_with_retry(
            f"{OLLAMA_BASE_URL}/api/embeddings",
            {"model": EMBED_MODEL, "prompt": text},
            timeout=EMBED_REQUEST_TIMEOUT_SECONDS,
            request_name="ollama_embedding"
        )

        embedding = data.get("embedding") or data.get("embeddings", [[]])[0]
        if not embedding:
            raise RuntimeError("Embedding generation failed. Empty embedding returned.")

        return embedding
    raise ValueError(f"Unsupported embedding provider: {EMBED_PROVIDER}")

# def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
def get_embeddings_batch(texts, batch_size=8):
    if EMBED_PROVIDER == "ollama":
        if not texts:
            return []

        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]

            data = post_json_with_retry(
                f"{OLLAMA_BASE_URL}/api/embed",
                {
                    "model": EMBED_MODEL,
                    "input": batch
                },
                timeout=EMBED_BATCH_REQUEST_TIMEOUT_SECONDS,
                request_name="ollama_batch_embedding"
            )

            embeddings = data.get("embeddings") or []
            if len(embeddings) != len(batch):
                raise RuntimeError("Batch embedding failed. Embedding count mismatch.")

            all_embeddings.extend(embeddings)

        if not all_embeddings:
            raise RuntimeError("Batch embedding failed. Empty embeddings returned.")

        return all_embeddings

    raise ValueError(f"Unsupported embedding provider: {EMBED_PROVIDER}")

# def get_embeddings_batch(texts, batch_size=8):
#     all_embeddings = []

#     for i in range(0, len(texts), batch_size):
#         batch = texts[i:i + batch_size]

#         response = requests.post(
#             f"{OLLAMA_BASE_URL}/api/embed",
#             json={
#                 "model": EMBED_MODEL,
#                 "input": batch
#             },
#             timeout=300
#         )

#         response.raise_for_status()
#         data = response.json()

#         all_embeddings.extend(data["embeddings"])

#     return all_embeddings

# def cosine_similarity(emb1: List[float], emb2: List[float]) -> float:
    
#     a = np.array(emb1)
#     b = np.array(emb2)
#     return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


# ---------------- Filter builder ----------------
# def build_where_filter(filters: dict | None = None):
#     if not filters:
#         return None

#     clean_filters = {
#         key: value
#         for key, value in filters.items()
#         if value not in [None, ""]
#     }

#     if not clean_filters:
#         return None

#     if len(clean_filters) == 1:
#         return clean_filters

#     return {
#         "$and": [{key: value} for key, value in clean_filters.items()]
#     }
# def build_where_filter(filters):
#     user_id = filters.get("user_id")
#     document_id = filters.get("document_id")
#     upload_session_id = filters.get("upload_session_id")

#     if document_id:
#         return {
#             "$and": [
#                 {"document_id": document_id},
#                 {"user_id": user_id}
#             ]
#         }

#     if upload_session_id:
#         return {
#             "$and": [
#                 {"upload_session_id": upload_session_id},
#                 {"user_id": user_id}
#             ]
#         }

#     return {"user_id": user_id}

def build_where_filter(filters: dict | None = None):
    filters = filters or {}

    user_id = filters.get("user_id")
    document_id = filters.get("document_id")
    upload_session_id = filters.get("upload_session_id")
    file_name = filters.get("file_name")
    page = filters.get("page")
    section = filters.get("section")
    chunk_type = filters.get("chunk_type")

    clean_filter = {}

    if user_id:
        clean_filter["user_id"] = user_id

    if document_id:
        clean_filter["document_id"] = document_id
    elif upload_session_id:
        clean_filter["upload_session_id"] = upload_session_id

    if file_name:
        clean_filter["file_name"] = file_name

    if page:
        clean_filter["page_number"] = page

    if section:
        clean_filter["section_title"] = section

    if chunk_type:
        clean_filter["chunk_type"] = chunk_type

    return clean_filter or None

# ---------------- RETRIEVE ----------------
def get_relevant_chunks(question: str):
    emb = get_embedding(question)

    results = qdrant.query(
        query_embeddings=[emb],
        n_results=TOP_K
    )
    
    return results["documents"][0]

# def query_rag(query):
    # print("\n\n\n\n\n 📚 Searching policy documents...")
    # print(f"\n ⚙️  [Generating query embedding...]")
    # emb = get_embedding(query)

    # print("\n\n\n\n\n 🔍 Finding relevant sections...")
    # print(f"\n ⚙️  [Querying vector DB + cosine similarity]")


    # results = collection.query(
    #     query_embeddings=[emb],
    #     n_results = 5,
    #     include=["documents", "metadatas", "embeddings"]
    # )
    # docs = results["documents"][0]
    # metas = results["metadatas"][0]
    # doc_embeddings = results["embeddings"][0]

    # response = []
    # """
    # docs, metas, and doc_embeddings are three parallel lists
    # zip(...) iterates over them together
    # each loop gets one doc, one matching meta, and one matching doc_emb
    # the loop stops when the shortest list runs out
    # """
    # for doc, meta, doc_emb in zip(docs, metas, doc_embeddings):
        
    #     similarity = cosine_similarity(emb, doc_emb)
    #     passes_test = similarity > 0.8  # Threshold for "passes test"
    #     # response.append({
    #     #     "content": doc,
    #     #     "page": meta.get("page"),
    #     #     "type": meta.get("type"),
    #     #     "similarity": round(similarity, 4),
    #     #     "passes_similarity_test": passes_test
    #     # })
    #     response.append({
    #         "content": doc,
    #         "page_number": meta.get("page_number"),
    #         "section_title": meta.get("section_title"),
    #         "chunk_type": meta.get("chunk_type"),
    #         "source_file": meta.get("source_file"),
    #         "document_id": meta.get("document_id"),
    #         "similarity": round(similarity, 4),
    #         "passes_similarity_test": passes_test
    #     })
    # print("\n\n\n\n\n 📄 Found 5 relevant chunks")
    # print(f"\n ⚙️  [Top-k retrieval complete]")
    # # final_result = []
    # # for content in response:
    # #     final_result.append(content["content"])

    # # return final_result 

    # return 

def update_where_filter_with_child_chunk(where_filter):
    return {
        **(where_filter or {}),
        "content_type": "child_chunk"
    }

def query_rag(query: str, filters: dict | None = None):
    print("\n\n\n 📚 Searching documents...")
    print("\n ⚙️ [Hybrid retrieval: Vector top 10 + BM25 top 10]")

    filters = filters or {}
    user_id = filters.get("user_id")

    if user_id and not filters.get("upload_session_id"):
        active_upload_session_ids = get_active_upload_session_ids(
            user_id,
            document_id=filters.get("document_id"),
        )

        if not active_upload_session_ids:
            return []

        filters = {
            **filters,
            "upload_session_id": active_upload_session_ids,
        }

    build_filter = build_where_filter(filters)
    where_filter = update_where_filter_with_child_chunk(build_filter)

    # vector_results = vector_search(query, top_k=20)
    # bm25_results = bm25_search(query, top_k=20)

    # vector_results = vector_search(query, top_k=10, where_filter=where_filter)
    # bm25_results = bm25_search(query, top_k=10, where_filter=where_filter)

    hybrid_search_child_result = hybrid_search_child_chunks(query, top_k=10, where_filter=where_filter)

    # parent_ids = extract_unique_parent_ids(hybrid_search_child_result)

    parent_ids = rank_parent_ids_from_children(child_results=hybrid_search_child_result, max_parents=2)

    upload_session_filter = filters.get("upload_session_id")
    if isinstance(upload_session_filter, str):
        upload_session_filter = [upload_session_filter]

    parent_chunks = fetch_parent_chunks(
        parent_ids,
        user_id=filters.get("user_id") if filters else None,
        upload_session_ids=upload_session_filter,
    )

    # # print(f"\n ⚙️ [Vector candidates: {len(vector_results)} | BM25 candidates: {len(bm25_results)}]")

    # fused_results = reciprocal_rank_fusion(
    #     vector_results=vector_results,
    #     bm25_results=bm25_results,
    #     k=60,
    #     max_candidates=12, #actual reranker workload
    # )

    # fused_results = []
    # print(f"\n ⚙️ [Merged candidates after RRF: {len(fused_results)}]")
    # print("\n ⚙️ [Reranking candidates → top 5]")

    # reranked_results = rerank_results(query, fused_results, top_k=5)

    # print("\n ⚙️ [Compressing context]")
    # compressed_results = compress_context_chunks(
    #     reranked_results,
    #     max_chars=12000,
    #     max_chunk_chars=3000,
    # )

    # response = []
    # for item in compressed_results:
    #     meta = item.get("metadata", {})
    #     response.append({
    #         "content": item.get("content", ""),
    #         "page_number": meta.get("page_number"),
    #         "section_title": meta.get("section_title"),
    #         "section_path": meta.get("section_path"),
    #         "chunk_type": meta.get("chunk_type"),
    #         "source_file": meta.get("source_file"),
    #         "document_id": meta.get("document_id"),
    #         "vector_score": round(item.get("vector_score", 0.0), 4),
    #         "bm25_score": round(item.get("bm25_score", 0.0), 4),
    #         "rrf_score": round(item.get("rrf_score", 0.0), 4),
    #         "rerank_score": round(item.get("rerank_score", 0.0), 4),
    #         "retrieved_by": item.get("sources", []),
    #     })

    # print(f"\n\n\n 📄 Final context chunks: {len(response)}")
    return parent_chunks


# ---------------- PROMPT ----------------
def build_context(chunks):
    context_blocks = []

    for i, chunk in enumerate(chunks, start=1):
        meta_line = (
            # f"[Source {i}] "
            # f"Document: {chunk.get('source_file') or 'Unknown'} | "
            f"Section: {chunk.get('section_title') or 'Unknown'} | "
            # f"Section Detail: {chunk.get('full_section') or 'Unknown'} | "
            # f"Section Path: {chunk.get('section_path') or 'Unknown'} | "
            # f"Page: {chunk.get('page_number') or 'Unknown'} | "
            # f"Type: {chunk.get('chunk_type') or 'text'} | "
            # f"Vector: {chunk.get('vector_score')} | "
            # f"BM25: {chunk.get('bm25_score')} | "
            # f"RRF: {chunk.get('rrf_score')} | "
            # f"Rerank: {chunk.get('rerank_score')}"
        )

        context_blocks.append(f"{meta_line}\n{chunk.get('content', '')}")
        
    print(f"context :{context_blocks}")
    return "\n\n---\n\n".join(context_blocks)

# def create_prompt(question: str, context: str):
#     return f"""
#                 You are a document-grounded AI assistant.

#                 Rules:
#                 - ONLY answer using the provided context.
#                 - Always mention the source document, section title, and page number when available.
#                 - If the answer is not found, say: "Not found in document."
#                 - Do not invent page numbers, section names, or policies.

#                 Answer style:
#                 Start with a direct answer.
#                 Then add evidence like:
#                 "According to <document>, section <section>, page <page>..."

#                 Context:
#                 {context}

#                 Question:
#                 {question}
#                 """

def create_prompt(question: str, context: str):
    return f"""
You are Assessly AI, a document-grounded assistant.

STRICT RULES:
1. Answer ONLY from the provided context, concise, professional, and human-readable paragraph.
2. Do not guess missing details.

CONTEXT:
{context}

QUESTION:
{question}

ANSWER:
"""
# 1. Answer ONLY from the provided context.
# 2. Keep answers concise, professional, and human-readable paragraph.
# 3. Prefer bullet points for lists or tabular data.
# 4. Avoid repetition and unnecessary explanations.
# 5. Do not guess missing details.
# 6. If answer is not present, reply exactly: "Not found in document."

# ---------------- LLM ----------------
def call_llm(prompt: str):
    try:
        logger.info("LLM inference started", extra={"prompt_length": len(prompt)})
        final_prompt = "/no_think\n\n" + prompt
        data = post_json_with_retry(
            f"{OLLAMA_BASE_URL}/api/generate",
            {
                "model": LLM_MODEL,
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

        logger.info("LLM inference completed")
        return data.get("response", "").strip()
        # response = requests.post(
        # f"{OLLAMA_BASE_URL}/api/chat",
        #     json={
        #         "model": LLM_MODEL,
        #         "messages": [
        #             {"role": "system", "content": "You are Assessly AI. Answer directly. Do not think step by step. Do not output reasoning."},
        #             {"role": "user", "content": "/no_think\n\n" + prompt}
        #         ],
        #         "stream": False,
        #         "options": {
        #             "temperature": 0,
        #             "top_p": 0.8, # limits token choices to the most probable 80% words/tokens, making answers more focused and less random.
        #             "repeat_penalty": 1.15, # penalizes repeated words/sentences, reducing verbose looping and repetition.
        #             "num_predict": 500,
        #             "num_ctx": 4096
        #         }
        #     },
        #     timeout=300
        # )

        # data = response.json()
        # return data["message"]["content"].strip()
    except ModelCallTimeout:
        return "The local AI model took too long to respond. Please try with a shorter question or smaller document context."
    except ModelCallError as e:
        logger.warning("LLM call failed", extra={"error": str(e)})
        return "The local AI model is temporarily unavailable. Please try again."
    except Exception:
        logger.exception("Unexpected LLM error")
        return "The local AI model failed unexpectedly. Please try again."


# ---------------- MAIN PIPELINE ----------------
# def generate_answer(question: str, filters: dict | None = None):
#     print("\n\n\n 🧠 Understanding your question...")
#     print(f"\n ⚙️  [Query received: {question}]\n")

#     chunks = query_rag(question, filters)

#     if not chunks:
#         return "No relevant content found." #Todo - error capture for phase

#     print("\n\n\n\n\n ✍️  Generating structured answer...")
#     print(f"\n ⚙️  [Prompt constructed → Sending to LLM]")
#     context = build_context(chunks)
#     prompt = create_prompt(question, context)

#     return call_llm(prompt)

# def calculate_confidence(chunks):
#     if not chunks:
#         return 0.0

#     rerank_scores = [c.get("rerank_score", 0.0) for c in chunks]
#     vector_scores = [c.get("vector_score", 0.0) for c in chunks]

#     avg_vector = sum(vector_scores) / len(vector_scores) if vector_scores else 0.0

#     if any(score > 0 for score in rerank_scores):
#         top_rerank = max(rerank_scores)
#         confidence = min(1.0, max(avg_vector, top_rerank / 10))
#     else:
#         confidence = avg_vector

#     return round(confidence, 2)


def build_citations(chunks):
    citations = []

    for i, chunk in enumerate(chunks, start=1):
        citations.append({
            "source": f"Source {i}",
            "document_id": chunk.get("document_id"),
            "file": chunk.get("source_file"),
            "page": chunk.get("page_number"),
            "section": chunk.get("section_title"),
            "section_path": chunk.get("section_path"),
            "chunk_type": chunk.get("chunk_type"),
            "vector_score": chunk.get("vector_score"),
            "bm25_score": chunk.get("bm25_score"),
            "rrf_score": chunk.get("rrf_score"),
            "rerank_score": chunk.get("rerank_score"),
            "retrieved_by": chunk.get("retrieved_by")
        })

    return citations


def validate_grounding(answer, chunks, confidence):
    answer_lower = answer.lower()

    if not chunks:
        return False

    if confidence < 0.45:
        return False

    if "not found" in answer_lower:
        return False

    has_source_reference = "[source" in answer_lower or "source " in answer_lower

    return has_source_reference


def generate_answer(question: str, filters: dict | None = None, progress_callback=None):
    logger.info("Generating answer")

    if progress_callback:
        progress_callback("retrieving", "Retrieving documents")

    chunks = query_rag(question, filters)

    if not chunks:
        return {
            "answer": "Not found in document.",
            "citations": [],
            "source_chunks": [],
            "confidence": 0.0,
            "is_grounded": False,
            "not_found": True,
            "validation_notes": [
                "No relevant chunks were retrieved from the knowledge base."
            ]
        }

    if progress_callback:
        progress_callback("reranking", "Reranking chunks")

    confidence = calculate_confidence(chunks)
    # Confidence should mostly be shown to the user, not used as the only decision-maker.
    # if confidence < 0.35:
    #     return {
    #         "answer": "Not found in document.",
    #         "citations": build_citations(chunks),
    #         "source_chunks": chunks,
    #         "confidence": confidence,
    #         "is_grounded": False,
    #         "not_found": True,
    #         "validation_notes": [
    #             "Retrieved chunks were too weak to answer safely."
    #         ]
    #     }
    if not chunks:
     return "Not found in document."

    logger.info("Prompt constructed; sending to LLM")

    if progress_callback:
        progress_callback("generating", "Generating answer")

    context = build_context(chunks)
    prompt = create_prompt(question, context)
    answer = call_llm(prompt)

    is_grounded = validate_grounding(answer, chunks, confidence)

    return {
        "answer": answer,
        # "citations": build_citations(chunks),
        # "source_chunks": chunks,
        # "confidence": confidence,
        # "is_grounded": is_grounded,
        # "not_found": "not found" in answer.lower(),
        # "validation_notes": [
        #     "Answer generated using retrieved context chunks.",
        #     "Citations are based on retrieved source metadata.",
        #     "Confidence is calculated from retrieval/reranking signals."
        # ]
    }
