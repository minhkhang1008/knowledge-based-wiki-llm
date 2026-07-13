from fastapi import FastAPI
from app.api.v1 import articles

app = FastAPI(
    title="Knowledge Based Wiki LLM API",
    description="API for parsing presentations and RAG",
    version="1.0.0"
)

app.include_router(articles.router, prefix="/api/v1/articles", tags=["Articles"])

@app.get("/")
def root():
    return {"message": "Hệ thống Wiki LLM đang hoạt động!"}