import os, sys

current_dir = os.path.dirname(os.path.abspath(__file__))
backend_root = os.path.abspath(os.path.join(current_dir, ".."))
if backend_root not in sys.path:
    sys.path.append(backend_root)

from backend.legacy.rag_query_sparkless import experiment_design_query
from backend.legacy.interview_state import InterviewState

class ExperimentDesignService:
    def answer_question(self, state: InterviewState, status_callback):
        return experiment_design_query(state, status_callback)