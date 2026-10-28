from typing import Any, Generic, Optional, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class APIError(BaseModel):
    code: int
    message: str
    details: Optional[Any] = None


class APIResponse(BaseModel, Generic[T]):
    data: Optional[T] = None
    error: Optional[APIError] = None


def api_success(data: Any) -> dict:
    """Helper to return consistent success envelope"""
    return {
        "data": data,
        "error": None
    }


def api_error(message: str, code: int = 400, details: Optional[Any] = None) -> dict:
    """Helper to return consistent error envelope"""
    return {
        "data": None,
        "error": {
            "code": code,
            "message": message,
            "details": details
        }
    }
