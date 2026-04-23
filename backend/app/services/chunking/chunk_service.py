from langchain.text_splitter import RecursiveCharacterTextSplitter
from uuid import uuid4 # uuid4 Generate random uuid
from .config import CHUNK_SIZE, CHUNK_OVERLAP, SEPARATORS
from app.models.chunk_model import Chunk

from .section_builder import build_sections
from .chunk_enricher import enrich_chunk
from .chunk_validator import validate_chunk
splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    separators=SEPARATORS,
)

def chunk_section(section, file_name):
    raw_chunks = splitter.split_text(section["content"])
    chunks = []

    for i, chunk_text in enumerate(raw_chunks):
        chunk = Chunk(
            id=str(uuid4()),
            content=chunk_text,
            metadata={
                "file":file_name,
                "section": section["title"],
                "chunk_index": i
            }
        )
        chunks.append(chunk)
    return chunks

def process_document(elements, file_name):
    print("\n\n\n\n\n 🧠 Understanding document layout...")
    print(f"\n ⚙️  [Analyzing headings, sections, tables]")

    
    sections = build_sections(elements)
    print("\n\n\n\n\n 🧩 Chunking content...")
    print(f"\n ⚙️  [Chunk size: 500 | Overlap: 100]")

    all_chunks = []
    print("\n\n\n\n\n 🔍 Enriching & validating chunks...")
    print(f"\n ⚙️  [Metadata tagging + quality checks]")	
    for section in sections:
        section_chunks = chunk_section(section, file_name)

        for chunk in section_chunks:
            chunk = enrich_chunk(chunk)

            if validate_chunk(chunk):
                all_chunks.append(chunk)


    return all_chunks