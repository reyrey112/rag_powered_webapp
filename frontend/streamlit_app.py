# streamlit_app.py
from dotenv import load_dotenv

load_dotenv()
import sys
import os
import streamlit as st
import uuid

current_dir = os.path.dirname(os.path.abspath(__file__))
root = os.path.abspath(os.path.join(current_dir, ".."))
if root not in sys.path:
    sys.path.append(root)

from backend import api_client as api

# # GCP Auth
# from google.auth.transport.requests import Request
# from google.oauth2 import id_token

GREETINGS = {
    "hi",
    "hello",
    "hey",
    "good morning",
    "good afternoon",
    "good evening",
    "howdy",
    "greetings",
    "thanks",
    "thank you",
    "ok",
    "okay",
    "got it",
    "sounds good",
    "great",
    "perfect",
    "yes",
    "no",
    "sure",
    "alright",
    "cool",
}


# def get_google_id_token() -> str:
#     """
#     Fetches an OIDC ID token from the Cloud Run metadata server at runtime.
#     """
#     # Cloud Run populates API_BASE_URL via your deploy.yml file
#     audience = os.environ.get("API_BASE_URL", "")

#     # Don't try hitting metadata server if running on local machine
#     if not audience or "localhost" in audience or "127.0.0.1" in audience:
#         return None

#     try:
#         # Fetches token securely using the container's service account
#         return id_token.fetch_id_token(Request(), audience)
#     except Exception:
#         return None


# # Fetch token and inject it directly into your backend client headers
# token = get_google_id_token()
# if token:
#     # This dynamically configures your api client instance to use the token
#     api.set_auth_token(token)

# Configs

st.set_page_config(page_title="Pharma RAG", page_icon="🔬", layout="centered")

st.title("🔬 Pharma RAG")
st.caption("Ask questions grounded in biomedical research literature")

# Session State
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
session_id = st.session_state.session_id

# UI conversation history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Minimal interview state init
if "interview" not in st.session_state:
    st.session_state.interview = {
        "active": False,
        "complete": False,
        "report_generated": False,
        "progress": "Question 1 of 5",
        "progress_ratio": "0/5",
    }
interview = st.session_state.interview

# Interview progress bar
if interview["active"] and not interview["complete"]:
    answered, total = (int(x) for x in interview["progress_ratio"].split("/"))
    st.progress(
        answered / total if total else 0,
        text=f"Gathering research context — {interview['progress']}",
    )

# Debug sidebar
if os.environ.get("DEBUG", "true").lower() == "true":
    with st.sidebar:
        st.caption(f"Session: {session_id[:8]}...")
        st.caption(f"Interview active: {interview['active']}")
        st.caption(f"Interview complete: {interview['complete']}")
        st.caption(f"Progress: {interview['progress']}")

# existing conversation rendering
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# Add message shorthand
def add_message(role: str, content: str):
    st.session_state.messages.append({"role": role, "content": content})


# Skip function
def is_skip(prompt: str) -> bool:
    return prompt.strip().lower() in {"skip", "s", "next", "proceed"}


# Create report after experiment design
def render_report(result: dict):
    st.markdown("## 📋 Experiment Design Report")
    st.divider()
    sections = [
        ("🔬 Background", "background"),
        ("🧪 Recommended Approach", "approach"),
        ("⚙️ Key Parameters", "parameters"),
        ("✅ Controls & Success Criteria", "controls"),
        ("⚠️ Risks & Mitigation", "risks"),
        ("🔭 Knowledge Gaps", "gaps"),
        ("📚 References", "references"),
    ]
    for label, key in sections:
        content = result["report"].get(key, "")
        if content:
            with st.expander(label, expanded=(key == "background")):
                st.markdown(content)

    with st.expander("🔎 Retrieval detail"):
        st.markdown(f"**Iterations:** {result['iterations']}")
        st.markdown(f"**Sufficient:** {result['sufficient']}")
        st.markdown("**Queries used:**")
        for i, q in enumerate(result["queries_used"], 1):
            st.markdown(f"{i}. {q}")


def run_experiment_design():
    """
    Extracted Path C logic — runs experiment design query and renders report.
    Called from Path B after last answer, and directly on rerun if complete.
    """
    with st.chat_message("assistant"):
        # Status container — retrieval progress only
        with st.status("Building your experiment design...", expanded=True) as status:

            try:
                result = api.interview_report(session_id)
                status.update(
                    label=f"✅ Report complete — {result['iterations']} search(es)",
                    state="complete",
                    expanded=False,
                )

            except Exception as e:
                status.update(
                    label="❌ Error generating report", state="error", expanded=True
                )
                st.error(str(e))
                result = None

        if result:
            render_report(result)
            add_message("assistant", "Experiment design report generated above.")
            interview.update(
                active=False,
                complete=True,
                report_generated=True,
                progress="Question 5 of 5",
                progress_ratio="5/5",
            )


def run_formality_call():
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            # Simple greetings don't need RAG — just a friendly reply
            reply = "Hello! Ask me a biomedical research question and I'll search the literature for you."
            st.markdown(reply)
    add_message("assistant", reply)


def run_skip_command():

    with st.chat_message("assistant"):
        msg = "Understood — proceeding with the context gathered so far."
        st.markdown(msg)
    add_message("assistant", msg)
    run_experiment_design()


def run_collect_answer(prompt: str):
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = api.interview_answer(prompt, session_id)

        if response["complete"]:
            # All questions answered — generate report
            # with st.chat_message("assistant"):
            msg = (
                "Thank you — I have everything I need. Let me search the literature..."
            )
            st.markdown(msg)
            add_message("assistant", msg)

            # with st.chat_message("assistant"):
            with st.status(
                "Building your experiment design...", expanded=True
            ) as status:
                try:
                    result = api.interview_report(session_id)
                    status.update(
                        label=f"✅ Report complete — {result['iterations']} search(es)",
                        state="complete",
                        expanded=False,
                    )
                except Exception as e:
                    status.update(
                        label="❌ Error generating report", state="error", expanded=True
                    )
                    st.error(str(e))
                    result = None

            if result:
                render_report(result)
                interview.update(
                    active=False,
                    complete=True,
                    report_generated=True,
                    progress=response["progress"],
                    progress_ratio=response["progress_ratio"],
                )
                add_message("assistant", "Experiment design report generated above.")

        else:
            # Next clarifying question
            # with st.chat_message("assistant"):
            st.markdown(response["question"])
            add_message("assistant", response["question"])
            interview["progress"] = response["progress"]


def start_new_interview(prompt: str):
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = api.interview_start(prompt, session_id)
        opening = (
            "Great research question! I have a few clarifying questions "
            "to help me find the most relevant literature.\n\n" + response["question"]
        )
        interview.update(
            active=True,
            complete=False,
            report_generated=False,
            progress=response["progress"],
            progress_ratio=response["progress_ratio"],
        )
        st.markdown(opening)
    add_message("assistant", opening)


def run_regular_rag(prompt, session_id):
    with st.chat_message("assistant"):
        result = None
        with st.status("Searching literature...", expanded=True) as status:
            try:
                result = api.query(prompt, session_id)
                if result["sufficient"]:
                    status.update(
                        label=f"✅ Found answer after {result['iterations']} search(es)",
                        state="complete",
                        expanded=False,
                    )
                else:
                    status.update(
                        label=f"⚠️ Partial context ({result['iterations']} searches)",
                        state="error",
                        expanded=False,
                    )
            except Exception as e:
                status.update(
                    label="❌ Error during retrieval", state="error", expanded=True
                )
                st.error(str(e))

        if result:
            st.markdown(result["answer"])

            if result["sources"]:
                with st.expander("📄 Sources"):
                    for source in result["sources"]:
                        st.markdown(f"- {source}")

            with st.expander("🔎 Retrieval detail"):
                st.markdown(f"**Iterations:** {result['iterations']}")
                st.markdown(f"**Sufficient:** {result['sufficient']}")
                st.markdown("**Queries used:**")
                for i, q in enumerate(result["queries_used"], 1):
                    st.markdown(f"{i}. {q}")

            add_message("assistant", result["answer"])


def is_greeting_or_formality(message: str) -> bool:
    """
    Returns True if the message is a greeting, acknowledgment,
    or other social formality that shouldn't trigger an interview.
    """
    cleaned = message.strip().lower().rstrip("!.,?")

    # Exact match against known greetings
    if cleaned in GREETINGS:
        return True

    # Short messages (under 15 chars) that aren't questions
    if len(cleaned) < 15 and "?" not in cleaned:
        return True

    return False


#  Handle new user input
if prompt := st.chat_input("Ask a research question..."):

    # Show user message
    add_message("user", prompt)
    with st.chat_message("user"):
        st.markdown(prompt)

    # ── Path F: Greeting or formality ─────────────────────────────────────────
    if is_greeting_or_formality(prompt) and not interview["active"]:
        run_formality_call()

    # ── Path A: Skip command ──────────────────────────────────────────────────
    elif is_skip(prompt) and interview["active"]:
        run_skip_command()

    # ── Path B: Interview in progress — collect answer ────────────────────────
    elif interview["active"] and not interview["complete"]:
        run_collect_answer(prompt)

    # ── Path D: Start new interview ───────────────────────────────────────────
    elif api.check_should_interview(prompt, session_id):
        start_new_interview(prompt)

    # ── Path E: Regular RAG (follow-up after report, or non-research question)
    else:
        run_regular_rag(prompt, session_id)
