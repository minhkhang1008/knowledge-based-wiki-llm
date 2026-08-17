from fastapi import APIRouter, Depends
from app.schemas.stats import StatsData, StatsResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.repositories.stats_repository import count_articles, count_qa_logs
from app.services.vector_index_maintenance import count_indexed_chunks

router = APIRouter()

@router.get("/api/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    total_articles = await count_articles(db)
    total_qa_logs = await count_qa_logs(db)
    total_indexed_chunks = count_indexed_chunks()

    data = StatsData(
        total_articles = total_articles,
        total_qa_logs = total_qa_logs,
        total_indexed_chunks = total_indexed_chunks
    )

    return StatsResponse(
        success = True,
        data = data,
        message = "Lấy stats thành công",
        error = None
    )
