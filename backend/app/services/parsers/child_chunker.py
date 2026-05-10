from langchain.text_splitter import RecursiveCharacterTextSplitter
import uuid

splitter = RecursiveCharacterTextSplitter(
    chunk_size=1200,
    chunk_overlap=150
)

def create_child_chunks(parents):

    children = []

    for parent in parents:

        full_text = "\n\n".join(parent["content"])

        chunks = splitter.split_text(full_text) # Note: prepare chunks as defined by splitter

        for idx, chunk in enumerate(chunks):

            children.append({
                "child_id": str(uuid.uuid4()),
                "parent_id": parent["parent_id"],
                "chunk_text": chunk,
                "section_title": parent["title"],
                "chunk_index": idx
            })

    return children