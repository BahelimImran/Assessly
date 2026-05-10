# docling_normalizer.py

import re
from typing import List, Dict, Any


def normalize_docling_markdown(markdown_text: str) -> List[Dict[str, Any]]:
    elements = []
    lines = markdown_text.splitlines()

    buffer = []
    table_buffer = []

    def flush_paragraph():
        nonlocal buffer
        text = " ".join(buffer).strip()
        if text:
            elements.append({
                "type": "paragraph",
                "text": text
            })
        buffer = []

    def flush_table():
        nonlocal table_buffer
        if table_buffer:
            table_md = "\n".join(table_buffer)
            elements.append({
                "type": "table",
                "table_markdown": table_md,
                "table_summary": summarize_table_basic(table_md)
            })
        table_buffer = []

    for line in lines:
        line = line.strip()

        if not line:
            flush_paragraph()
            flush_table()
            continue

        # Heading: ## 4.1 WELL SITE
        heading_match = re.match(r"^(#{1,6})\s+(.*)", line)
        if heading_match:
            flush_paragraph()
            flush_table()

            elements.append({
                "type": "heading",
                "level": len(heading_match.group(1)),
                "text": heading_match.group(2).strip()
            })
            continue

        # Markdown table row
        if "|" in line and line.startswith("|"):
            flush_paragraph()
            table_buffer.append(line)
            continue

        # Markdown image: ![](image.png)
        image_match = re.match(r"!\[.*?\]\((.*?)\)", line)
        if image_match:
            flush_paragraph()
            flush_table()

            elements.append({
                "type": "image",
                "image_path": image_match.group(1),
                "image_caption": ""
            })
            continue

        buffer.append(line)

    flush_paragraph()
    flush_table()

    return elements


def summarize_table_basic(table_md: str) -> str:
    lines = [line for line in table_md.splitlines() if "|" in line]

    if not lines:
        return ""

    header = lines[0].replace("|", " ").strip()
    row_count = max(len(lines) - 2, 0)

    return f"Table about {header}. Contains {row_count} data rows."