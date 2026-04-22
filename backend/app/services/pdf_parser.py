from unstructured.partition.pdf import partition_pdf
import re

def is_good_parse(elements):

    if not elements:
        return False
    
    texts = [ el.text or "" for el in elements]
    total_text = " ".join(texts).strip()

    if len(total_text) < 500:
        return False
    
    if len(elements) < 5:
        return False
    
    words = re.findall(r"\b[a-zA-Z]{3,}\b", total_text)
    if len(words) < 50:
        return False

    return True

def parse_pdf(file_path: str):
    # """
    # Parse pdf into structure elements (text, tables, images, etc.)
    # """
    # Parse pdf into structure elements (text, tables, images, etc.)

    # First try fast no OCR
    elements = partition_pdf(
        filename=file_path,
        strategy="hi_res", #Important for layout detection
        infer_table_structure=True,
        include_page_breaks=True,
        chunking_strategy=None, 

    )

    # check quality
    if not is_good_parse(elements):
        print("Falling back to OCR (hi_res)")

        elements = partition_pdf(
            filename = file_path,
            strategy = "hi_res"
        )

    return elements