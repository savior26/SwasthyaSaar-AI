from pydantic import BaseModel
from typing import Optional


class TestGraphPoint(BaseModel):
    date: Optional[str] = None
    value: float
    unit: Optional[str] = None
    flag: Optional[str] = None


class TestGraphResponse(BaseModel):
    test_name: str
    unit: Optional[str] = None
    data: list[TestGraphPoint]