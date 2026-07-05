from fastapi import APIRouter
from schema.AskRequestSchema import AskRequest
from schema.AskResponseSchema import AskResponse

router = APIRouter()

@router.post("/api/qa/ask")
def askQuestion(question: AskRequest):
    data_response = AskResponse(
        answer = "Đây là câu trả lời test tự động",
        sources = [
            {"test" : "test"}
        ]
    )
    return {
        "success" : True,
        "data" : data_response,
        "message" : "chạy thành công",
        "error" : None
    }