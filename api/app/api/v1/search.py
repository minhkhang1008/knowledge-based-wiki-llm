from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.schemas.AskResponseSchema import AskResponse, dataResponse  
from app.services.services_vector_db import semantic_search_logic 

router = APIRouter()

#Pydantic model
class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Câu truy vấn tìm kiếm ngữ nghĩa")


@router.post("/search", response_model=AskResponse)
async def search(request: SearchRequest):
    try:
        chunks = await semantic_search_logic(request.query)

        # chunks là list[dict] với keys: text, article_id, source_file, page_number
        answer_text = "\n\n".join(chunk["text"] for chunk in chunks)
        
        sources = [
            {
                "article_id": chunk["article_id"],
                "source_file": chunk["source_file"],
                "page_number": chunk["page_number"],
            }
            for chunk in chunks
        ]

        data = dataResponse(
            answer=answer_text,
            sources=sources,
        )

        return AskResponse(
            success=True,
            data=data,
            message="Tìm kiếm thành công" if chunks else "Không tìm thấy kết quả phù hợp",
            error=None,
        )
    
    except Exception as e:
        return AskResponse(
            success=False,
            data=dataResponse(answer="", sources=[]),
            message="Tìm kiếm thất bại",
            error=str(e),
        )