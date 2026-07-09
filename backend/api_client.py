import os
import httpx

API_BASE = os.environ.get("API_BASE_URL", "http://localhost:8000")
TIMEOUT  = 120  # Long for now for RAG calls

def query(prompt: str, session_id: str) -> dict:
    r = httpx.post(f"{API_BASE}/query", json={
        "prompt": prompt,
        "session_id": session_id,
    }, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

def interview_start(prompt: str, session_id: str) -> dict:
    r = httpx.post(f"{API_BASE}/interview/start", json={
        "prompt": prompt,
        "session_id": session_id,
    }, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

def interview_answer(answer: str, session_id: str) -> dict:
    r = httpx.post(f"{API_BASE}/interview/answer", json={
        "answer": answer,
        "session_id": session_id,
    }, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

def interview_report(session_id: str) -> dict:
    r = httpx.post(f"{API_BASE}/interview/report", json={
        "session_id": session_id,
    }, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

def check_should_interview(prompt: str, session_id: str) -> bool:
    r = httpx.post(f"{API_BASE}/interview/should-start", json={
        "prompt": prompt,
        "session_id": session_id,
    }, timeout=30)
    r.raise_for_status()
    return r.json()["should_start"]

def check_greeting(prompt: str) -> bool:
    r = httpx.post(f"{API_BASE}/interview/is-greeting", json={
        "prompt": prompt,
        "session_id": "",
    }, timeout=10)
    r.raise_for_status()
    return r.json()["is_greeting"]