from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from agent import ReportAgent

app = FastAPI(title="Financial Report Q&A")

agent = ReportAgent()

@app.on_event("startup")
async def startup_event():
    if not agent.load_index():
        raise RuntimeError("FAISS index not found. Please run index_builder.py to build the index before starting the API.")

class QuestionRequest(BaseModel):
    question: str

@app.post("/ask")
async def ask_question(request: QuestionRequest):
    try:
        answer = agent.ask_question(request.question)
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
