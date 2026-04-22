def process_elements(elements, source_file):

    # Convert parse elements to documents + metadata

    documents = []
    metadatas = []

    for el in elements:
        text = getattr(el, "text", "") # Todo

        if not text or not text.strip(): # Todo
            continue

        category = el.category

        
        metadata = {
            "source" : source_file,
            "page" : getattr(el.metadata, "page_number", None), # Todo
            "type" : category
        }

        # Smart Handling
        if category == "Table":
            text = f"Table data:\n{text}"

        elif category == "Image":
            text = f"Image content detected (need OCR/vision processing)"
        
        documents.append(text)
        metadatas.append(metadata)


    return documents, metadatas