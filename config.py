import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Base path
    BASE_DIR = Path(__file__).parent

    # PDF folder for downloaded reports
    PDF_FOLDER = str(BASE_DIR / "downloaded_pdfs")

    # FAISS index path
    FAISS_PATH = str(BASE_DIR / "data/faiss_index")

    # Record of indexed file hashes
    INDEXED_FILES_RECORD = str(BASE_DIR / "data/processed_hashes.json")

    # OpenAI
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    EMBEDDING_MODEL = "text-embedding-3-small"

    # Chunking parameters
    CHUNK_SIZE = 512
    CHUNK_OVERLAP = 50

    @classmethod
    def validate(cls):
        """Ensure necessary directories exist and OpenAI key is present."""
        os.makedirs(cls.PDF_FOLDER, exist_ok=True)
        os.makedirs(os.path.dirname(cls.FAISS_PATH), exist_ok=True)

        if not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not found in environment. Please check your .env file.")
