import os
import httpx, logging
import google.auth.transport.requests
import google.oauth2.id_token

API_BASE = os.environ.get("API_BASE_URL", "http://localhost:8000")

API_AUDIENCE = os.environ.get("API_AUDIENCE", "http://localhost:8000")
TIMEOUT = 120


def _get_identity_token() -> str | None:
    """
    Fetches a GCP identity token for service-to-service auth.
    Returns None when running locally (no metadata server available).
    """
    try:
        auth_req = google.auth.transport.requests.Request()
        token = google.oauth2.id_token.fetch_id_token(auth_req, API_AUDIENCE)

        print(f"Token audience: {API_AUDIENCE}")
        logging.debug(f"{API_AUDIENCE}")
        print(f"Token fetched successfully: {token[:20]}...")
        logging.debug(f"Token fetched successfully: {token[:20]}...")

        return token
    except Exception:
        return None


def _headers() -> dict:
    token = _get_identity_token()
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


def query(prompt: str, session_id: str) -> dict:
    r = httpx.post(
        f"{API_BASE}/query",
        json={
            "prompt": prompt,
            "session_id": session_id,
        },
        headers=_headers(),
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


def interview_start(prompt: str, session_id: str) -> dict:
    r = httpx.post(
        f"{API_BASE}/interview/start",
        json={
            "prompt": prompt,
            "session_id": session_id,
        },
        headers=_headers(),
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


def interview_answer(answer: str, session_id: str) -> dict:
    r = httpx.post(
        f"{API_BASE}/interview/answer",
        json={
            "answer": answer,
            "session_id": session_id,
        },
        headers=_headers(),
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


def interview_report(session_id: str) -> dict:
    r = httpx.post(
        f"{API_BASE}/interview/report",
        json={
            "session_id": session_id,
        },
        headers=_headers(),
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


def check_should_interview(prompt: str, session_id: str) -> bool:
    r = httpx.post(
        f"{API_BASE}/interview/should-start",
        json={
            "prompt": prompt,
            "session_id": session_id,
        },
        headers=_headers(),
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["should_start"]
