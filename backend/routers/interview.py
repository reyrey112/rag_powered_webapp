import os, sys

current_dir = os.path.dirname(os.path.abspath(__file__))
backend_root = os.path.abspath(os.path.join(current_dir, ".."))
if backend_root not in sys.path:
    sys.path.append(backend_root)

from fastapi import APIRouter, HTTPException
from models.requests import InterviewAnswerRequest, InterviewStartRequest, InterviewReportRequest
from models.responses import InterviewQuestionResponse, ReportResponse
from legacy.interview_state import (
    InterviewState,
    generate_interview_question,
    should_start_interview,
    save_interview_state,
    load_interview_state,
)
from legacy.rag_query_sparkless import experiment_design_query
from legacy.conversation_history import read_history

router = APIRouter(prefix="/interview", tags=["interview"])


@router.post("/start", response_model=InterviewQuestionResponse)
async def start_interview(request: InterviewStartRequest):
    state = InterviewState()
    state.original_question = request.prompt
    state.active = True
    first_category = state.next_category()
    first_question = generate_interview_question(state, first_category)
    state.record_question(first_category, first_question)
    save_interview_state(request.session_id, state)
    return InterviewQuestionResponse(
        question=first_question,
        progress=state.progress_label(),
        progress_ratio=f"{state.answered_count()}/{state.total_questions()}",
        complete=False,
    )


@router.post("/answer", response_model=InterviewQuestionResponse)
async def answer_interview(request: InterviewAnswerRequest):
    state = load_interview_state(request.session_id)
    if not state:
        raise HTTPException(
            status_code=404, detail="No active interview for this session"
        )
    last_category = state.asked_categories[-1] if state.asked_categories else None
    if last_category:
        state.record_answer(last_category, request.answer)
    if state.is_complete():
        state.complete = True
        save_interview_state(request.session_id, state)
        return InterviewQuestionResponse(
            question="Interview complete. Generating report...",
            progress=state.progress_label(),
            progress_ratio=f"{state.answered_count()}/{state.total_questions()}",
            complete=True,
        )
    next_category = state.next_category()
    next_question = generate_interview_question(state, next_category)
    state.record_question(next_category, next_question)
    save_interview_state(request.session_id, state)
    return InterviewQuestionResponse(
        question=next_question,
        progress=state.progress_label(),
        progress_ratio=f"{state.answered_count()}/{state.total_questions()}",
        complete=False,
    )


@router.post("/report", response_model=ReportResponse)
async def generate_report(request: InterviewReportRequest):
    state = load_interview_state(request.session_id)
    if not state:
        raise HTTPException(status_code=404, detail="No interview state found")
    result = experiment_design_query(state=state)
    report = {
        "report": result["report"],
        "iterations": result["iterations"],
        "sufficient": result["sufficient"],
        "queries_used": result["queries_used"],
    }
    print(report)
    save_interview_state(request.session_id, InterviewState())  # reset
    return ReportResponse(**report)


@router.post("/should-start")
async def should_start(req: InterviewStartRequest):
    history = read_history(req.session_id)
    state = load_interview_state(req.session_id) or InterviewState()
    result = should_start_interview(req.prompt, state, history)
    return {"should_start": result}
