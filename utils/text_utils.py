def chunk_text(text: str, chunk_size=1000, overlap=200) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks

def simple_search(chunks: list[str], query: str, top_k=3) -> list[str]:
    scored = [(chunk.lower().count(query.lower()), chunk) for chunk in chunks if query.lower() in chunk.lower()]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:top_k]] if scored else chunks[:top_k]
