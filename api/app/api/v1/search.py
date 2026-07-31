from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
import httpx

from app.schemas.AskResponse import AskResponse, DataResponse  
from app.services.services_vector_db import semantic_search_logic
from app.schemas.SearchData import SearchData
from app.schemas.SearchResponse import SearchResponse
from app.schemas.ErrorResponse import ErrorResponse
from app.schemas.ErrorFormat import ErrorFormat
from app.schemas.SourceResponse import SourceResponse

router = APIRouter()

#Pydantic model
# class SearchRequest(BaseModel):
#     query: str = Field(..., min_length=1, description="Câu truy vấn tìm kiếm ngữ nghĩa")

@router.get("/api/search", response_model=SearchResponse)
async def search(request: str, top_k: int = 5, filters: dict[str, str] | None = None):
    chunks = await semantic_search_logic(request, top_k, filters)

    # chunks là list[dict] với keys: text, article_id, source_file, page_number

    return SearchResponse(
        success = True,
        data = SearchData(results = chunks),
        message = "Tìm kiếm thành công" if chunks else "Không tìm thấy kết quả phù hợp",
        error = None
    )