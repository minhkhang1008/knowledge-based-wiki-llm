from typing import Annotated

from fastapi import APIRouter
from pydantic import BaseModel, StringConstraints

from app.schemas.SearchData import SearchData
from app.schemas.SearchResponse import SearchResponse
from app.services.services_vector_db import semantic_search_logic


router = APIRouter()

QueryText = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=2,
    ),
]


class SearchRequest(BaseModel):
    query: QueryText


@router.post("/api/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    chunks = await semantic_search_logic(request.query)

    return SearchResponse(
        success=True,
        data=SearchData(results=chunks),
        message=(
            "Tìm kiếm thành công"
            if chunks
            else "Không tìm thấy kết quả phù hợp"
        ),
        error=None,
    )
