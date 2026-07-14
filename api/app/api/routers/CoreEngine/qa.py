from fastapi import APIRouter
from app.schemas.AskRequestSchema import AskRequest
from app.schemas.AskResponseSchema import AskResponse

from app.core.ollama_client import generate_chat, generate_embedding
from app.services.services_vector_db import search_similar_chunks
from app.services.prompt_builder import build_rag_prompt

from app.models.qa_log import log_qa_interaction

router = APIRouter()

@router.post("/api/qa/ask")
async def askQuestion(question: AskRequest):

    question_vector = await generate_embedding(question.question)
    chunks = search_similar_chunks(question_vector, top_k=5)
    prompt = build_rag_prompt(question.question, chunks)
    ai_response = await generate_chat(prompt)   

    data_response = {
        "answer" : ai_response,
        "sources" : chunks
    }
    await log_qa_interaction(question=question.question, answer=ai_response, sources=chunks)
    return AskResponse(
        success = True,
        data = data_response,
        message = "Xử lí câu hỏi RAG thành công",
        error = None
    )