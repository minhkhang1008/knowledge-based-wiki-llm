from fastapi import APIRouter
from schema.AskRequestSchema import AskRequest
from schema.AskResponseSchema import AskResponse, AskSource


from api.app.core.ollama_client import generate_chat, generate_embedding
from api.app.services.services_vector_db import search_similar_chunks
from api.app.services.prompt_builder import build_rag_prompt

from api.app.models.qa_log import log_qa_interaction

router = APIRouter()

@router.post("/api/qa/ask")
async def askQuestion(question: AskRequest):

    question_vector = await generate_embedding(question.question)
    chunks = search_similar_chunks(question_vector, top_k=5)
    prompt = build_rag_prompt(question.question, chunks)
    ai_response = await generate_chat(prompt)   

    data_response = [
        AskResponse(
            answer = ai_response
        ),
        chunks
    ]
    await log_qa_interaction(_question=question.question, _answer=ai_response, _source=chunks)
    return {
        "success" : True,
        "data" : data_response,
        "message" : "Xử lý câu hỏi RAG thành công.",
        "error" : None
    }