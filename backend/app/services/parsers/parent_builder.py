import uuid

def build_parent_sections(elements):

    parents = []

    current_section = None

    for el in elements:

        if el["type"] == "heading":

            if current_section:
                parents.append(current_section)

            current_section = {
                "parent_id": str(uuid.uuid4()),
                "title": el["text"],
                "content": [],
                "elements": []
            }

        elif current_section:

            current_section["elements"].append(el)

            if el["type"] == "paragraph":
                current_section["content"].append(el["text"])

            elif el["type"] == "table":
                current_section["content"].append(
                    f"TABLE:\n{el['table_summary']}\n{el['table_markdown']}"
                )

            elif el["type"] == "image":
                current_section["content"].append(
                    f"IMAGE:\n{el.get('image_caption', '')}"
                )

    if current_section:
        parents.append(current_section)

    return parents