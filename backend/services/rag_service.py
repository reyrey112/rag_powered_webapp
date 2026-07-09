import os, sys

current_dir = os.path.dirname(os.path.abspath(__file__))
backend_root = os.path.abspath(os.path.join(current_dir, ".."))
if backend_root not in sys.path:
    sys.path.append(backend_root)

from backend.legacy.rag_query_sparkless import rag_query

class RagService:
    def answer_question(self, prompt: str, history: list, status_callback):
        return rag_query(prompt, history, status_callback)