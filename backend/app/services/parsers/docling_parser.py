"""
1. table_markdown extraction
2. table chunks
3. child chunks with sentence-aware overlap
4. parent chunks
5. retrieval: child search → parent context
***************
1. Search child chunks
2. Read parent_chunk_id from metadata
3. Fetch parent chunks by parent_chunk_id
4. Send parent section as final context
*********
Child chunk improves retrieval accuracy.
Parent chunk gives complete context to answer correctly.
More accurate search + better answer context
"""

import re
from typing import Optional
from pathlib import Path
from typing import Any, Dict, List
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling_core.types.doc import ImageRefMode, PictureItem, TableItem

from app.services.parsers.vision_service import call_ollama_vision
import hashlib

###############
# from docling.document_converter import DocumentConverter
from app.services.parsers.docling_normalizer import normalize_docling_markdown
from app.services.parsers.parent_builder import build_parent_sections
from app.services.parsers.child_chunker import create_child_chunks


def estimate_tokens(text: str) -> int:
    return max(1, len(text.split()) * 1.3)


def split_sentences(text: str) -> List[str]:
    return re.split(r'(?<=[.!?])\s+', text.strip())


def chunk_text_with_overlap(
    text: str,
    max_words: int = 220,
    overlap_sentences: int = 2
) -> List[str]:
    sentences = split_sentences(text)
    chunks = []
    current = []

    for sentence in sentences:
        current.append(sentence)

        if len(" ".join(current).split()) >= max_words:
            chunks.append(" ".join(current).strip())
            current = current[-overlap_sentences:]

    if current:
        chunks.append(" ".join(current).strip())

    return chunks

def extract_table_markdown(table: TableItem) -> str:
    try:
        return table.export_to_markdown()
    except Exception:
        pass

    try:
        return table.export_to_dataframe().to_markdown(index=False)
    except Exception:
        pass

    try:
        return str(table.text)
    except Exception:
        return ""


def extract_table_columns(table_markdown: str) -> List[str]:
    lines = [line.strip() for line in table_markdown.splitlines() if line.strip()]

    if not lines:
        return []

    first_line = lines[0]

    if "|" in first_line:
        return [
            col.strip()
            for col in first_line.strip("|").split("|")
            if col.strip()
        ]

    return []


def summarize_table(table_markdown: str, caption: str = "") -> str:
    columns = extract_table_columns(table_markdown)

    if columns:
        return f"This table contains structured information with columns: {', '.join(columns)}."

    if caption:
        return f"This table describes: {caption}"

    return "This table contains structured information extracted from the document."

# def build_docling_chunks(parsed: Dict[str, Any]) -> List[Dict[str, Any]]:
#     markdown = parsed["markdown"]
#     source_file = parsed["source_file"]

#     chunks = []
#     current_title = "Document Start"
#     current_content = []
#     section_index = 0

#     def flush_section():
#         nonlocal section_index, current_title, current_content

#         section_text = "\n".join(current_content).strip()

#         if not section_text:
#             return

#         section_index += 1
#         # parent_chunk_id = f"section_{section_index}"
#         # parent_chunk_id = hashlib.md5(
#         # f"{source_file}_{current_title}_{section_index}".encode()
#         # ).hexdigest()

#         parent_chunk_id = f"{source_file}_{current_title}_{section_index}"


#         # Parent chunk
#         chunks.append({
#             "chunk_role": "parent",
#             "parent_chunk_id": parent_chunk_id,
#             "title": current_title,
#             "section_title": current_title,
#             "section_path": current_title,
#             "content": section_text,
#             "source_file": source_file,
#             "chunk_type": "section",
#             "parser": "docling",
#         })

#         # Child chunks
#         child_chunks = chunk_text_with_overlap(
#             section_text,
#             max_words=220,
#             overlap_sentences=2
#         )

#         for child_index, child_text in enumerate(child_chunks):
#             chunks.append({
#                 "chunk_role": "child",
#                 "parent_chunk_id": parent_chunk_id,
#                 "child_index": child_index,
#                 "title": current_title,
#                 "section_title": current_title,
#                 "section_path": current_title,
#                 "content": child_text,
#                 "source_file": source_file,
#                 "chunk_type": "text",
#                 "parser": "docling",
#             })

#     for line in markdown.splitlines():
#         clean_line = line.strip()

#         if not clean_line:
#             continue

#         if clean_line.startswith("#"):
#             flush_section()

#             heading_level = len(clean_line) - len(clean_line.lstrip("#"))
#             current_title = clean_line.replace("#", "").strip()
#             current_content = []
#         else:
#             current_content.append(clean_line)

#     flush_section()

#     # Add table chunks separately
#     table_count = 0

#     for item in parsed["visual_items"]:
#         if item["type"] == "table":
#             table_count += 1

#             table_markdown = item.get("table_markdown", "")
#             caption = item.get("caption", "")
#             columns = extract_table_columns(table_markdown)
#             table_summary = summarize_table(table_markdown, caption)
#             vision_summary = item.get("vision_summary", "")

#             content = f"""
#             Table: {caption or f"Table {table_count}"}

#             {table_markdown}

#             Summary:
#             {table_summary}

#             Vision Summary:
#             {vision_summary}

#             """.strip()

#             chunks.append({
#                 "chunk_role": "child",
#                 "parent_chunk_id": f"table_{table_count}",
#                 "title": caption or f"Table {table_count}",
#                 "section_title": caption or f"Table {table_count}",
#                 "section_path": caption or f"Table {table_count}",
#                 "content": content,
#                 "source_file": source_file,
#                 "chunk_type": "table",
#                 "table_markdown": table_markdown,
#                 "table_summary": table_summary,
#                 "columns": columns,
#                 "image_path": item.get("path", ""),
#                 "parser": "docling",
#             })

#         if item["type"] == "figure":
#             figure_title = item.get("caption") or f"Figure {item.get('index')}"

#             content = f"""
#             Figure: {figure_title}

#             Caption:
#             {item.get("caption", "")}

#             Vision Summary:
#             {item.get("vision_summary", "")}

#             Image Type:
#             Technical Diagram / Chart / Screenshot
#             """.strip()

#             chunks.append({
#                 "chunk_role": "child",
#                 "parent_chunk_id": f"figure_{item.get('index')}",
#                 "title": figure_title,
#                 "section_title": figure_title,
#                 "section_path": figure_title,
#                 "content": content,
#                 "source_file": source_file,
#                 "chunk_type": "figure",
#                 "image_path": item.get("path", ""),
#                 "vision_summary": item.get("vision_summary", ""),
#                 "parser": "docling+vision",
#             })

#     return chunks

def make_stable_id(*parts: str) -> str:
    raw = "||".join([str(p) for p in parts if p])
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def split_large_parent_text(
    text: str,
    max_words: int = 1500,
    overlap_sentences: int = 3
) -> List[str]:
    return chunk_text_with_overlap(
        text=text,
        max_words=max_words,
        overlap_sentences=overlap_sentences
    )


def build_docling_chunks(parsed: Dict[str, Any]) -> List[Dict[str, Any]]:
    markdown = parsed["markdown"]
    source_file = parsed["source_file"]

    chunks = []
    current_content = []
    section_index = 0
    heading_stack: List[str] = []

    def current_section_path() -> str:
        return " > ".join(heading_stack) if heading_stack else "Document Start"

    def flush_section():
        nonlocal section_index, current_content

        section_text = "\n".join(current_content).strip()
        if not section_text:
            return

        section_title = heading_stack[-1] if heading_stack else "Document Start"
        section_path = current_section_path()

        parent_parts = split_large_parent_text(
            section_text,
            max_words=1500,
            overlap_sentences=3
        )

        for parent_part_index, parent_text in enumerate(parent_parts):
            section_index += 1

            parent_chunk_id = make_stable_id(
                source_file,
                section_path,
                str(section_index),
                str(parent_part_index),
                parent_text[:300]
            )

            parent_metadata = {
                "chunk_role": "parent",
                "parent_chunk_id": parent_chunk_id,
                "title": section_title,
                "section_title": section_title,
                "section_path": section_path,
                "content": parent_text,
                "source_file": source_file,
                "chunk_type": "section",
                "parser": "docling",
                "parent_part_index": parent_part_index,
                "word_count": len(parent_text.split()),
            }

            chunks.append(parent_metadata)

            child_chunks = chunk_text_with_overlap(
                parent_text,
                max_words=350,
                overlap_sentences=3
            )

            for child_index, child_text in enumerate(child_chunks):
                chunks.append({
                    "chunk_role": "child",
                    "parent_chunk_id": parent_chunk_id,
                    "child_index": child_index,
                    "title": section_title,
                    "section_title": section_title,
                    "section_path": section_path,
                    "content": child_text,
                    "source_file": source_file,
                    "chunk_type": "text",
                    "parser": "docling",
                    "word_count": len(child_text.split()),
                    "searchable_content": f"{section_path}\n\n{child_text}",
                })

        current_content = []

    for line in markdown.splitlines():
        clean_line = line.strip()

        if not clean_line:
            continue

        if clean_line.startswith("#"):
            flush_section()

            heading_level = len(clean_line) - len(clean_line.lstrip("#"))
            title = clean_line.replace("#", "").strip()

            heading_stack[:] = heading_stack[:heading_level - 1]
            heading_stack.append(title)

            current_content = []
        else:
            current_content.append(clean_line)

    flush_section()

    # Visual chunks: keep them searchable, but do not pretend they have full parent context yet.
    table_count = 0
    figure_count = 0

    for item in parsed["visual_items"]:
        if item["type"] == "table":
            table_count += 1

            table_markdown = item.get("table_markdown", "")
            caption = item.get("caption", "")
            columns = extract_table_columns(table_markdown)
            table_summary = summarize_table(table_markdown, caption)
            vision_summary = item.get("vision_summary", "")

            table_id = make_stable_id(
                source_file,
                "table",
                str(table_count),
                caption,
                table_markdown[:300]
            )

            content = f"""
Table: {caption or f"Table {table_count}"}

{table_markdown}

Summary:
{table_summary}

Vision Summary:
{vision_summary}
""".strip()

            chunks.append({
                "chunk_role": "child",
                "parent_chunk_id": table_id,
                "child_index": 0,
                "title": caption or f"Table {table_count}",
                "section_title": caption or f"Table {table_count}",
                "section_path": caption or f"Table {table_count}",
                "content": content,
                "searchable_content": f"{caption}\n{table_summary}\n{vision_summary}\n{table_markdown}",
                "source_file": source_file,
                "chunk_type": "table",
                "table_markdown": table_markdown,
                "table_summary": table_summary,
                "columns": columns,
                "image_path": item.get("path", ""),
                "parser": "docling",
            })

            chunks.append({
                "chunk_role": "parent",
                "parent_chunk_id": table_id,
                "title": caption or f"Table {table_count}",
                "section_title": caption or f"Table {table_count}",
                "section_path": caption or f"Table {table_count}",
                "content": content,
                "source_file": source_file,
                "chunk_type": "table_parent",
                "parser": "docling",
            })

        elif item["type"] == "figure":
            figure_count += 1
            figure_title = item.get("caption") or f"Figure {figure_count}"

            figure_id = make_stable_id(
                source_file,
                "figure",
                str(figure_count),
                figure_title
            )

            content = f"""
Figure: {figure_title}

Caption:
{item.get("caption", "")}

Vision Summary:
{item.get("vision_summary", "")}

Image Type:
Technical Diagram / Chart / Screenshot
""".strip()

            chunks.append({
                "chunk_role": "child",
                "parent_chunk_id": figure_id,
                "child_index": 0,
                "title": figure_title,
                "section_title": figure_title,
                "section_path": figure_title,
                "content": content,
                "searchable_content": content,
                "source_file": source_file,
                "chunk_type": "figure",
                "image_path": item.get("path", ""),
                "vision_summary": item.get("vision_summary", ""),
                "parser": "docling+vision",
            })

            chunks.append({
                "chunk_role": "parent",
                "parent_chunk_id": figure_id,
                "title": figure_title,
                "section_title": figure_title,
                "section_path": figure_title,
                "content": content,
                "source_file": source_file,
                "chunk_type": "figure_parent",
                "parser": "docling+vision",
            })

    return chunks


def should_use_vision(item: Dict[str, Any]) -> bool:

    if item["type"] == "figure":
        return True

    if item["type"] == "table":
        markdown = item.get("table_markdown", "")

        # weak extraction
        if len(markdown.strip()) < 50:
            return True

        # complex table
        if markdown.count("|") > 20:
            return True

    return False

def enrich_visual_items_with_vision(visual_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    for item in visual_items:
        image_path = item.get("path")

        if not image_path:
            continue

        if item["type"] == "table":
            prompt = """
            Extract the meaning of this table.
            Return:
            1. table purpose
            2. key columns
            3. important relationships
            4. short searchable summary
            """
        elif item["type"] == "figure":
            prompt = """
            Explain this figure for a RAG knowledge base.
            Return:
            1. what the image shows
            2. important labels/text
            3. key meaning
            4. short searchable summary
            """
        else:
            continue

        item["vision_summary"] = call_ollama_vision(
            image_path=image_path,
            prompt=prompt
        )

    return visual_items

def parse_pdf_with_docling(
        file_path: str, 
        output_root: str = "storage/parsed",
        use_ocr: bool = False) -> Dict[str, Any]:
    
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {file_path}")

    output_dir = (Path(output_root) / path.stem).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    markdown_path = output_dir / f"{path.stem}.md"
    artifacts_dir = output_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    pipeline_options = PdfPipelineOptions()

    # Important for visual preservation
    pipeline_options.images_scale = 2
    pipeline_options.generate_page_images = False
    pipeline_options.generate_picture_images = True
    pipeline_options.generate_table_images = True

    # OCR
    pipeline_options.do_ocr =  use_ocr
    
    # Important for math PDFs
    pipeline_options.do_formula_enrichment = False

    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )

    result = converter.convert(str(path))
    document = result.document

    # Export markdown with referenced images
    # markdown_path = output_dir / f"{path.stem}.md"
    # document.save_as_markdown(markdown_path, image_mode=ImageRefMode.REFERENCED)

    document.save_as_markdown(
    markdown_path,
    image_mode=ImageRefMode.REFERENCED,
    artifacts_dir=artifacts_dir
    )

    #Text markdown
    markdown_text = markdown_path.read_text(encoding="utf-8")

    page_images = []
    for page_no, page in document.pages.items():
        image_path = output_dir / f"page_{page.page_no}.png"
        if page.image and page.image.pil_image:
            page.image.pil_image.save(image_path, format="PNG")
            page_images.append({
                "page": page.page_no,
                "type": "page_image",
                "path": str(image_path)
            })

    visual_items = []
    table_count = 0
    picture_count = 0

    for element, level in document.iterate_items():
        if isinstance(element, TableItem):
            table_count += 1
            table_path = output_dir / f"table_{table_count}.png"

            try:
                element.get_image(document).save(table_path, "PNG")
            except Exception:
                table_path = ""

            table_markdown = extract_table_markdown(element)

            visual_items.append({
                "type": "table",
                "index": table_count,
                "path": str(table_path),
                "caption": extract_caption(element),
                "table_markdown": table_markdown,
                "columns": extract_table_columns(table_markdown),
            })

        elif isinstance(element, PictureItem):
            picture_count += 1
            picture_path = output_dir / f"figure_{picture_count}.png"
            element.get_image(document).save(picture_path, "PNG")

            visual_items.append({
                "type": "figure",
                "index": picture_count,
                "path": str(picture_path),
                "caption": extract_caption(element),
            })
    
    filtered_items = [
        item for item in visual_items
        if should_use_vision(item)
    ]

    enriched_visual_items = enrich_visual_items_with_vision(filtered_items)

    return {
        "parser": "docling",
        "source_file": path.name,
        "output_dir": str(output_dir),
        "markdown": markdown_text,
        "markdown_path": str(markdown_path),
        "page_images": page_images,
        "visual_items": visual_items,
        "enriched_visual_items" : enriched_visual_items,
        "quality": check_parse_quality(markdown_text, visual_items),
    }

def extract_caption(element):
    try:
        captions = getattr(element, "captions", [])

        texts = []
        for c in captions:
            txt = getattr(c, "text", "").strip()
            if txt:
                texts.append(txt)

        return " ".join(texts)

    except Exception:
        return ""

def check_parse_quality(markdown: str, visual_items: List[Dict[str, Any]]) -> Dict[str, Any]:
    text = markdown.strip()
    word_count = len(text.split())

    image_placeholders = markdown.count("<!-- image -->")
    has_math_loss = any(token in markdown for token in ["1 2", "3 4", "4 4", "5 12"])

    score = 100

    if word_count < 100:
        score -= 40

    if image_placeholders > 0:
        score -= 15

    if has_math_loss:
        score -= 20

    if len(visual_items) > 0:
        score += 10

    return {
        "word_count": word_count,
        "visual_items": len(visual_items),
        "image_placeholders": image_placeholders,
        "possible_math_loss": has_math_loss,
        "score": max(min(score, 100), 0),
        "needs_visual_processing": image_placeholders > 0 or has_math_loss,
    }

def parse_document(file_path: str) -> Dict[str, Any]:
    # parsed = parse_pdf_with_docling(file_path, use_ocr=False)
    # parsed = parse_pdf_to_elements(file_path)
    # if parsed["quality"]["score"] < 60:
    #     parsed = parse_pdf_with_docling(file_path, use_ocr=True)
    #     parsed = parse_pdf_to_elements(file_path)
    # chunks = build_docling_chunks(parsed)

    elements = parse_pdf_to_elements(file_path)
    parent_chunks = build_parent_sections(elements)
    child_chunks = create_child_chunks(parent_chunks)
    return {
        "parent_chunks": parent_chunks,
        "child_chunks": child_chunks,
    }
############################################################
def parse_pdf_to_elements(pdf_path: str):
    converter = DocumentConverter()
    result = converter.convert(pdf_path)

    markdown_text = result.document.export_to_markdown()

    elements = normalize_docling_markdown(markdown_text)

    return elements