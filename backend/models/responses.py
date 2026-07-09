from pydantic import BaseModel
from typing import Optional

class QueryResponse(BaseModel):
    answer: str
    sources: list[str]
    iterations: int
    sufficient: bool
    queries_used: list[str]
    chunk_ids: list[str]

class InterviewQuestionResponse(BaseModel):
    question: str
    progress: str        # "Question 1 of 5" — human readable for display
    progress_ratio: str  # "1/5" — for the progress bar calculation
    complete: bool

class ReportResponse(BaseModel):
    report: dict
    iterations: int
    sufficient: bool
    queries_used: list[str]