from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.qa_log import QALog
from app.models.article import Article
async def count_articles(
    session: AsyncSession,
) -> int: 
    try:
        stmt = select(func.count()).select_from(Article)
        res = await session.scalar(stmt)
        return res or 0
    except Exception:
        await session.rollback()
        raise
async def count_qa_logs(
    session: AsyncSession,
) -> int:
    try: 
        stmt = select(func.count()).select_from(QALog)
        res = await session.scalar(stmt)
        return res or 0 
    except Exception:
        await session.rollback();
        raise
        
