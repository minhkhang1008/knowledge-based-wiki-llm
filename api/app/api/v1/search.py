from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
import httpx

from app.schemas.AskResponse import AskResponse, dataResponse  
from app.services.services_vector_db import semantic_search_logic
from app.schemas.SearchData import searchData
from app.schemas.SearchResponse import searchResponse
from app.schemas.ErrorResponse import errorResponse
from app.schemas.ErrorFormat import errorFormat
from app.schemas.SourceResponse import sourceResponse

router = APIRouter()

#Pydantic model
# class SearchRequest(BaseModel):
#     query: str = Field(..., min_length=1, description="Câu truy vấn tìm kiếm ngữ nghĩa")

@router.get("/api/search", response_model=searchResponse)
async def search(request: searchData):
    try:
        chunks = await semantic_search_logic(request.query)

        # chunks là list[dict] với keys: text, article_id, source_file, page_number

        return searchResponse(
            success = True,
            data = chunks,
            message = "Tìm kiếm thành công" if chunks else "Không tìm thấy kết quả phù hợp",
            error = None
        )
    except (httpx.RequestError, httpx.HTTPError, ConnectionError) as e:
        content = errorResponse(
            success=False,
            data=None,
            message="Ollama ngoại tuyến",
            error=errorFormat(code="503", detail=str(e))
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=content.model_dump()
        )
    except Exception as e:
        content = errorResponse(
            success=False,
            data=None,
            message="Lỗi không dự kiến",
            error=errorFormat(code="500", detail=str(e))
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=content.model_dump()
        )