# docling_normalizer.py

import re
from typing import List, Dict, Any


# def normalize_docling_markdown(markdown_text: str) -> List[Dict[str, Any]]:
#     elements = []
#     lines = markdown_text.splitlines()

#     buffer = []
#     table_buffer = []

#     def flush_paragraph():
#         nonlocal buffer
#         text = " ".join(buffer).strip()
#         if text:
#             elements.append({
#                 "type": "paragraph",
#                 "text": text
#             })
#         buffer = []

#     def flush_table():
#         nonlocal table_buffer
#         if table_buffer:
#             table_md = "\n".join(table_buffer)
#             elements.append({
#                 "type": "table",
#                 "table_markdown": table_md,
#                 "table_summary": summarize_table_basic(table_md)
#             })
#         table_buffer = []

#     for line in lines:
#         line = line.strip()

#         if not line:
#             flush_paragraph()
#             flush_table()
#             continue

#         # Heading: ## 4.1 WELL SITE
#         heading_match = re.match(r"^(#{1,6})\s+(.*)", line)
#         if heading_match:
#             flush_paragraph()
#             flush_table()

#             elements.append({
#                 "type": "heading",
#                 "level": len(heading_match.group(1)),
#                 "text": heading_match.group(2).strip()
#             })
#             continue

#         # Markdown table row
#         if "|" in line and line.startswith("|"):
#             flush_paragraph()
#             table_buffer.append(line)
#             continue

#         # Markdown image: ![](image.png)
#         image_match = re.match(r"!\[.*?\]\((.*?)\)", line)
#         if image_match:
#             flush_paragraph()
#             flush_table()

#             elements.append({
#                 "type": "image",
#                 "image_path": image_match.group(1),
#                 "image_caption": ""
#             })
#             continue

#         buffer.append(line)

#     flush_paragraph()
#     flush_table()

#     return elements

# def normalize_docling_markdown(markdown_text: str) -> List[Dict[str, Any]]:
#     elements: List[Dict[str, Any]] = []

#     lines = markdown_text.splitlines()

#     paragraph_buffer: List[str] = []
#     table_buffer: List[str] = []

#     current_heading = None
#     current_heading_level = None

#     def build_metadata(chunk_type: str, content_type: str) -> Dict[str, Any]:
#         return {
#             "chunk_type": chunk_type,
#             "content_type": content_type,
#             "section_title": current_heading,
#             "section_level": current_heading_level,
#         }

#     def flush_paragraph():
#         nonlocal paragraph_buffer

#         text = " ".join(paragraph_buffer).strip()

#         if text:
#             elements.append({
#                 "type": "paragraph",
#                 "text": text,
#                 "retrieval_text": text,
#                 "ocr_text": "",
#                 "image_summary": "",
#                 "metadata": build_metadata(
#                     chunk_type="text",
#                     content_type="paragraph"
#                 )
#             })

#         paragraph_buffer = []

#     def flush_table():
#         nonlocal table_buffer

#         if table_buffer:
#             table_md = "\n".join(table_buffer).strip()
#             table_summary = summarize_table_basic(table_md)

#             retrieval_text = f"{table_summary}\n{table_md}".strip()

#             elements.append({
#                 "type": "table",
#                 "text": table_summary,
#                 "table_markdown": table_md,
#                 "table_summary": table_summary,
#                 "retrieval_text": retrieval_text,
#                 "ocr_text": "",
#                 "image_summary": "",
#                 "metadata": build_metadata(
#                     chunk_type="table",
#                     content_type="table"
#                 )
#             })

#         table_buffer = []

#     for line in lines:
#         line = line.strip()

#         if not line:
#             flush_paragraph()
#             flush_table()
#             continue

#         # Heading
#         heading_match = re.match(r"^(#{1,6})\s+(.*)", line)
#         if heading_match:
#             flush_paragraph()
#             flush_table()

#             current_heading_level = len(heading_match.group(1))
#             current_heading = heading_match.group(2).strip()

#             elements.append({
#                 "type": "heading",
#                 "level": current_heading_level,
#                 "text": current_heading,
#                 "retrieval_text": current_heading,
#                 "ocr_text": "",
#                 "image_summary": "",
#                 "metadata": build_metadata(
#                     chunk_type="heading",
#                     content_type="heading"
#                 )
#             })
#             continue

#         # Table row
#         if "|" in line and line.startswith("|"):
#             flush_paragraph()
#             table_buffer.append(line)
#             continue

#         # Image/chart
#         image_match = re.match(r"!\[(.*?)\]\((.*?)\)", line)
#         if image_match:
#             flush_paragraph()
#             flush_table()

#             alt_text = image_match.group(1).strip()
#             image_path = image_match.group(2).strip()

#             elements.append({
#                 "type": "image",
#                 "text": alt_text,
#                 "image_path": image_path,
#                 "image_caption": alt_text,
#                 "ocr_text": "",
#                 "image_summary": "",
#                 "retrieval_text": alt_text,
#                 "metadata": build_metadata(
#                     chunk_type="image",
#                     content_type="visual"
#                 )
#             })
#             continue

#         paragraph_buffer.append(line)

#     flush_paragraph()
#     flush_table()

#     return elements

# def summarize_table_basic(table_md: str) -> str:
#     lines = [line for line in table_md.splitlines() if "|" in line]

#     if not lines:
#         return ""

#     header = lines[0].replace("|", " ").strip()
#     row_count = max(len(lines) - 2, 0)

#     return f"Table about {header}. Contains {row_count} data rows."