from fastapi import APIRouter, Depends
from app.schemas.AskRequest import AskRequest
from app.schemas.AskResponse import AskResponse, DataResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.rag_service import process_rag_pipeline
from app.core.database import get_db
from app.repositories.qa_log_repository import log_qa_interaction
from app.schemas.ErrorResponse import ErrorResponse
from app.schemas.ErrorFormat import ErrorFormat

router = APIRouter()

@router.post("/api/qa/ask")
async def askQuestion(question: AskRequest, db: AsyncSession = Depends(get_db)):
    rag_result = await process_rag_pipeline(question.question, question.chat_history)

    await log_qa_interaction(db, question.question, rag_result["answer"], rag_result["sources"])
    return AskResponse(
        success = True,
        data = DataResponse(
            answer = rag_result["answer"],
            sources = rag_result["sources"],
            no_answer_reason = rag_result["no_answer_reason"]
        ),
        message = "Xử lí câu hỏi RAG thành công",
        error = None
    )