import os
import json
from openai import OpenAI
from .config import Config  # Relative import

client = OpenAI(api_key=Config.OPENAI_API_KEY)

def get_embedding(text: str, model: str = "text-embedding-3-large") -> list:
    try:
        response = client.embeddings.create(
            input=[text],
            model=model
        )
        return response.data[0].embedding
    except Exception as e:
        raise Exception(f"Failed to generate embedding: {str(e)}")

def search_vector_stores(query: str) -> str:
    try:
        processed_pdfs_file = os.path.join(os.path.dirname(__file__), "..", "data", "processed_pdfs.json")
        print(f"Loading processed_pdfs from: {processed_pdfs_file}")
        with open(processed_pdfs_file, "r") as f:
            processed_pdfs = json.load(f)
        
        print(f"Found {len(processed_pdfs)} vector stores: {list(processed_pdfs.keys())}")
        if not processed_pdfs:
            print("No vector stores found.")
            return ""
        
        best_match = ""
        for pdf_name, data in processed_pdfs.items():
            vector_store_id = data["vector_store_id"]
            print(f"Searching vector store {vector_store_id} for query: {query}")
            response = client.vector_stores.search(
                vector_store_id=vector_store_id,
                query=query,
                top_k=1  # Retrieve the top 1 match
            )
            print(f"Search response for {vector_store_id}: {response.data}")
            if response.data:
                best_match = response.data[0].text if hasattr(response.data[0], "text") else response.data[0].content if hasattr(response.data[0], "content") else str(response.data[0])
                print(f"Found match: {best_match}")
                break
        
        return best_match
    except Exception as e:
        print(f"Failed to search vector stores: {str(e)}")
        return ""

def generate_completion(prompt: str, model: str = "gpt-4o-mini", temperature: float = 0.7, max_tokens: int = 500) -> str:
    try:
        context = search_vector_stores(prompt)
        print(f"Retrieved context: {context}")
        if context:
            prompt = f"Context from financial reports:\n{context}\n\n{prompt}"
        else:
            print("No context retrieved, relying on model knowledge.")
        
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content
    except Exception as e:
        raise Exception(f"Failed to generate completion: {str(e)}")

ANALYSIS_PROMPT_TEMPLATE = """
You are a financial analyst. Given the following excerpts from a company's financial reports, provide a detailed analysis focusing on:

- Revenue trends
- Risk and challenges
- Growth opportunities
- Any anomalies or important points

Summarize the key points clearly and concisely.

Report excerpts:
{report_text}

Analysis:
"""

def analyze_report(chunks: list) -> str:
    try:
        combined_text = "\n\n".join(chunks)
        prompt = ANALYSIS_PROMPT_TEMPLATE.format(report_text=combined_text)
        return generate_completion(prompt)
    except Exception as e:
        raise Exception(f"Failed to analyze report: {str(e)}")
