from typing import Any, Optional

def success_response(data: Any = None, message: str = "") -> dict:
    """Định dạng phản hồi API thành công chuẩn của team."""
    return {
        "success": True,
        "data": data,
        "message": message,
        "error": None
    }

def error_response(code: str, detail: str, message: str = "Validation failed") -> dict:
    """Định dạng phản hồi API lỗi chuẩn của team."""
    return {
        "success": False,
        "data": None,
        "message": message,
        "error": {
            "code": code,
            "detail": detail
        }
    }