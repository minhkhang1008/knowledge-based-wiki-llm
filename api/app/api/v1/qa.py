from fastapi import APIRouter, Depends
from app.schemas.AskRequestSchema import AskRequest
from app.schemas.AskResponseSchema import AskResponse, dataResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.rag_service import process_rag_pipeline
from app.core.database import get_db
from app.models.qa_log import log_qa_interaction

router = APIRouter()

@router.post("/api/qa/ask")
async def askQuestion(question: AskRequest, db: AsyncSession = Depends(get_db)):

    rag_result = await process_rag_pipeline(question.question)

    await log_qa_interaction(question=question.question, answer=rag_result["answer"], source=rag_result["sources"])
    return AskResponse(
        success = True,
        data = dataResponse(
            answer = rag_result["answer"],
            source = rag_result["sources"]
        ),
        message = "Xử lí câu hỏi RAG thành công",
        error = rag_result["no_answer_reason"]
    )
