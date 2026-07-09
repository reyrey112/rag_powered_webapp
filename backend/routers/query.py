import os, sys

current_dir = os.path.dirname(os.path.abspath(__file__))
backend_root = os.path.abspath(os.path.join(current_dir, ".."))
if backend_root not in sys.path:
    sys.path.append(backend_root)

from fastapi import APIRouter

from models.requests import QueryRequest
from models.responses import QueryResponse
from legacy.conversation_history import read_history, write_history
from legacy.rag_query_sparkless import rag_query

router = APIRouter(prefix="/query", tags=["query"])

@router.post("", response_model=QueryResponse)
async def query(request: QueryRequest):
    history = read_history(request.session_id)
    result = rag_query(request.prompt, history=history)
    write_history(
        session_id=request.session_id,
        user_message=request.prompt,
        assistant_response=result["answer"],
        query_used=str(result["queries_used"]),
        chunks_retrieved=result["chunk_ids"],
    )
    return QueryResponse(**result)    
