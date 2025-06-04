import os
import json
import hashlib
from config import Config
from llm_utils import generate_completion
from vector_db import VectorDB
from utils import extract_text_from_pdf, chunk_text

class ReportAgent:
    def __init__(self, pdf_folder=Config.PDF_FOLDER, faiss_path=Config.FAISS_PATH):
        self.pdf_folder = pdf_folder
        self.faiss_path = faiss_path
        self.vector_db = VectorDB(faiss_path=self.faiss_path)
        self.text_chunks = []
        self.hashes_file = Config.INDEXED_FILES_RECORD
        self.processed_hashes = self.load_processed_hashes()

    def load_processed_hashes(self):
        if os.path.exists(self.hashes_file):
            with open(self.hashes_file, "r") as f:
                return json.load(f)
        return {}

    def save_processed_hashes(self):
        os.makedirs(os.path.dirname(self.hashes_file), exist_ok=True)
        with open(self.hashes_file, "w") as f:
            json.dump(self.processed_hashes, f, indent=2)

    def file_hash(self, filepath):
        """Compute SHA256 hash of a file."""
        hasher = hashlib.sha256()
        with open(filepath, "rb") as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        return hasher.hexdigest()

    def build_or_load_index(self):
        # Find new or updated PDFs
        new_or_updated_files = []
        for filename in os.listdir(self.pdf_folder):
            if filename.lower().endswith(".pdf"):
                full_path = os.path.join(self.pdf_folder, filename)
                current_hash = self.file_hash(full_path)
                if filename not in self.processed_hashes or self.processed_hashes[filename] != current_hash:
                    new_or_updated_files.append((filename, full_path, current_hash))

        # If no new files, try loading existing index and chunks
        if not new_or_updated_files and self.vector_db.load_index():
            print("Loaded existing FAISS index and text chunks. No new or updated PDFs found.")
            self.text_chunks = self.load_chunks()
            return

        # Otherwise, rebuild index with new/updated PDFs plus existing chunks
        print(f"Processing {len(new_or_updated_files)} new or updated PDFs and rebuilding index...")

        all_chunks = []

        # Load existing chunks if index already exists
        if self.vector_db.load_index():
            self.text_chunks = self.load_chunks()
            all_chunks.extend(self.text_chunks)

        # Extract and chunk text from new/updated files
        for filename, full_path, filehash in new_or_updated_files:
            text = extract_text_from_pdf(full_path)
            chunks = chunk_text(text)
            all_chunks.extend(chunks)
            self.processed_hashes[filename] = filehash

        if not all_chunks:
            raise ValueError("No text chunks found in PDFs.")

        # Build and save the new index
        self.text_chunks = all_chunks
        self.vector_db.build_index(all_chunks)
        self.save_chunks(all_chunks)
        self.save_processed_hashes()
        print("Index built and saved.")

    def load_index(self):
        # Load existing FAISS index and chunks without rebuilding
        if self.vector_db.load_index():
            self.text_chunks = self.load_chunks()
            print("Loaded existing FAISS index and text chunks.")
            return True
        else:
            print("No existing FAISS index found.")
            return False

    def ask_question(self, question, top_k=5):
        results = self.vector_db.search(question, top_k=top_k)
        retrieved_chunks = [chunk for _, chunk in results]

        prompt = (
            "You are a skilled financial data analyst. Using the following excerpts from financial reports, "
            "carefully analyze the information and provide a clear, concise, and insightful answer to the question below.\n\n"
            f"Question: {question}\n\n"
            "Report excerpts:\n"
            + "\n\n".join(retrieved_chunks) +
            "\n\nPlease base your response strictly on the data provided and highlight key insights, trends, or anomalies relevant to the question."
        )
        response = generate_completion(prompt)
        return response

    def save_chunks(self, chunks):
        os.makedirs(os.path.dirname(self.faiss_path), exist_ok=True)
        with open(self.faiss_path + "_chunks.txt", "w", encoding="utf-8") as f:
            for chunk in chunks:
                f.write(chunk.replace("\n", " ") + "\n")

    def load_chunks(self):
        chunks_path = self.faiss_path + "_chunks.txt"
        if os.path.exists(chunks_path):
            with open(chunks_path, "r", encoding="utf-8") as f:
                return [line.strip() for line in f.readlines()]
        return []
