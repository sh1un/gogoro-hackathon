import json


def text_to_json(text, search_results):
    formatted_text = text.replace("\\n", "\n")

    formatted_sources = []
    for result in search_results:
        chapter = result["fields"]["chapter"][0]
        document = result["fields"]["document"][0].replace("\\n", "\n")
        formatted_sources.append(
            {
                "order": len(formatted_sources) + 1,
                "similarity_score": result["_score"],
                "chapter": chapter,
                "document": document,
            }
        )

    total_score = sum(source["similarity_score"] for source in formatted_sources)

    output_json = {
        "answer": formatted_text,
        "sources_count": len(formatted_sources),
        "similarity_score": total_score,
        "sources": formatted_sources,
    }

    json_str = json.dumps(output_json, ensure_ascii=False)

    return json_str
