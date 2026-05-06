from typing import Any

from pydantic import BaseModel


def ok(data: Any = None, msg: str = "success") -> dict:
    return {"code": 0, "msg": msg, "data": data}


def fail(msg: str = "error", code: int = 400) -> dict:
    return {"code": code, "msg": msg, "data": None}


class PageData(BaseModel):
    list: list[Any]
    total: int
    page: int
    page_size: int
