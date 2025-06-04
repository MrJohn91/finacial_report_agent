import os
import faiss
import numpy as np
from llm_utils import get_embedding
from config import Config

class VectorDB:
    def __init__(self, faiss_path=Config.FAISS_PATH):
        self.faiss_path = faiss_path
        self.index = None
        self.text_chunks = []  # Store original text chunks in memory
        self.dimension = 0

    def build_index(self, texts):
        """Build FAISS index from list of text chunks."""
        self.text_chunks = texts
        embeddings = [get_embedding(t) for t in texts]
        embeddings_np = np.array(embeddings).astype('float32')

        self.dimension = embeddings_np.shape[1]
        self.index = faiss.IndexFlatL2(self.dimension)
        self.index.add(embeddings_np)
        self.save_index()

    def save_index(self):
        """Save FAISS index and text chunks to disk."""
        os.makedirs(os.path.dirname(self.faiss_path), exist_ok=True)
        faiss.write_index(self.index, self.faiss_path)

        # Save text chunks alongside index with consistent naming
        chunks_path = self.faiss_path + "_chunks.txt"
        with open(chunks_path, "w", encoding="utf-8") as f:
            for chunk in self.text_chunks:
                f.write(chunk.replace("\n", " ") + "\n")

    def load_index(self):
        """Load FAISS index and text chunks from disk."""
        if os.path.exists(self.faiss_path):
            self.index = faiss.read_index(self.faiss_path)
            self.dimension = self.index.d

            chunks_path = self.faiss_path + "_chunks.txt"
            if os.path.exists(chunks_path):
                with open(chunks_path, "r", encoding="utf-8") as f:
                    self.text_chunks = [line.strip() for line in f.readlines()]
            return True
        return False

    def search(self, query, top_k=5):
        """Search the index for top_k similar chunks to the query text.

        Returns:
            List of (distance, chunk) tuples for top_k results.
        """
        if self.index is None:
            raise RuntimeError("Index not loaded")

        query_embedding = np.array([get_embedding(query)]).astype('float32')
        distances, indices = self.index.search(query_embedding, top_k)

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < len(self.text_chunks):
                results.append((dist, self.text_chunks[idx]))
        return results
