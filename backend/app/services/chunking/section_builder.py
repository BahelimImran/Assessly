def build_sections(elements):
    print("\n\n\n\n\n ✂️  Splitting into semantic sections...")
    print(f"\n ⚙️  [Section builder initialized]")
    sections = []
    current_section = {
        "title": "Unknown",
        "content": ""
    }

    previous_tuple = {
        "title": "",
        "content": ""
    }
    for el in elements:
        if previous_tuple["title"] == el.category:
            previous_tuple["title"] = previous_tuple["content"]
            sections.append(previous_tuple)

        if el.category == 'Title': # fix of - 'Title' object is not subscriptable
            if current_section["content"]:
                sections.append(current_section)

            current_section = {
                "title": el.text,
                "content": ""
            }

            previous_tuple = {
                "title": 'Title',
                "content": el.text
            }
        else:
            current_section["content"] =  current_section["content"] + el.text + "\n"
            previous_tuple["title"] = ''
    if current_section["content"]:
        sections.append(current_section)

    return sections