from fastapi import APIRouter
from app.schemas.AskRequestSchema import AskRequest
from app.schemas.AskResponseSchema import AskResponse, dataResponse

from app.services.rag_service import process_rag_pipeline

from app.models.qa_log import log_qa_interaction

router = APIRouter()

@router.post("/api/qa/ask")
async def askQuestion(question: AskRequest):

    rag_result = await process_rag_pipeline(question.question)

    await log_qa_interaction(question=question.question, answer=rag_result["answer"], sources=rag_result["sources"])
    return AskResponse(
        success = True,
        data = dataResponse(
            answer = rag_result["answer"],
            sources = rag_result["sources"]
        ),
        message = "Xử lí câu hỏi RAG thành công",
        error = rag_result["no_answer_reason"]
    )