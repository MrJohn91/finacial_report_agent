import os
import json
import hashlib
from config import Config
from utils import extract_text_from_pdf, chunk_text
from vector_db import VectorDB

def file_hash(filepath):
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()

def load_processed_hashes():
    if os.path.exists(Config.INDEXED_FILES_RECORD):
        with open(Config.INDEXED_FILES_RECORD, "r") as f:
            return json.load(f)
    return {}

def save_processed_hashes(hashes):
    os.makedirs(os.path.dirname(Config.INDEXED_FILES_RECORD), exist_ok=True)
    with open(Config.INDEXED_FILES_RECORD, "w") as f:
        json.dump(hashes, f, indent=2)

def build_index():
    pdf_folder = Config.PDF_FOLDER
    faiss_path = Config.FAISS_PATH
    vector_db = VectorDB(faiss_path=faiss_path)
    processed_hashes = load_processed_hashes()

    new_or_updated_files = []
    for filename in os.listdir(pdf_folder):
        if filename.lower().endswith(".pdf"):
            full_path = os.path.join(pdf_folder, filename)
            current_hash = file_hash(full_path)
            if filename not in processed_hashes or processed_hashes[filename] != current_hash:
                new_or_updated_files.append((filename, full_path, current_hash))

    if not new_or_updated_files:
        print("No new or updated PDFs found. Index rebuild skipped.")
        return

    print(f"Processing {len(new_or_updated_files)} new or updated PDFs and rebuilding index...")

    all_chunks = []
    for filename, full_path, filehash in new_or_updated_files:
        text = extract_text_from_pdf(full_path)
        chunks = chunk_text(text)
        all_chunks.extend(chunks)
        processed_hashes[filename] = filehash

    if not all_chunks:
        raise ValueError("No text chunks found in PDFs.")

    vector_db.build_index(all_chunks)

    # Save chunks to file for later retrieval
    os.makedirs(os.path.dirname(faiss_path), exist_ok=True)
    chunks_path = str(faiss_path) + "_chunks.txt"
    with open(chunks_path, "w", encoding="utf-8") as f:
        for chunk in all_chunks:
            f.write(chunk.replace("\n", " ") + "\n")

    save_processed_hashes(processed_hashes)
    print("Index built and saved successfully.")

if __name__ == "__main__":
    build_index()
