from utils.file_utils import extract_texts_from_folder
from utils.text_utils import chunk_text, simple_search

# folder_path: Path to the folder containing text files.
# chunk_size: Maximum size of each text chunk (default 1000 characters).
# overlap: Overlap size between chunks to maintain context (default 200 characters).
# top_k: Number of top search results to return (default 3).

class KnowledgeBase:
    def __init__(self, folder_path, chunk_size=1000, overlap=200, top_k=3):
        self.folder_path = folder_path
        self.chunk_size = chunk_size
        self.chunk_overlap = overlap
        self.top_k = top_k
        self._load_kb()

    def _load_kb(self):
        combined_text = extract_texts_from_folder(self.folder_path)
        self.chunks = chunk_text(combined_text, self.chunk_size, self.chunk_overlap)

    def query(self, question: str) -> list[str]:
        return simple_search(self.chunks, question, self.top_k)
