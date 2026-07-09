from pydantic import BaseModel
from typing import Optional

class QueryRequest(BaseModel):
    prompt: str
    session_id: str
    history: Optional[list] = []

class InterviewStartRequest(BaseModel):
    prompt: str
    session_id: str

class InterviewAnswerRequest(BaseModel):
    answer: str
    session_id: str

class InterviewReportRequest(BaseModel):
    session_id: str