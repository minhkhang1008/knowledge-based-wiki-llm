from fastapi import APIRouter
from schema.AskRequestSchema import AskRequest
from schema.AskResponseSchema import AskResponse

router = APIRouter()

@router.post("/api/qa/ask")
def askQuestion(question: AskRequest):
    data_response = AskResponse(
        answer = "Đây là câu trả lời test tự động",
        sources = [
            {
                "id" : "wiki_05",
                "title" : "Quy chế nhân sự 2025",
                "url" : "/articles/wiki_05"
            }
        ]
    )
    return {
        "success" : True,
        "data" : data_response,
        "message" : "Xử lý câu hỏi RAG thành công.",
        "error" : None
    }