# import pytest, os, sys
# from unittest.mock import MagicMock, patch, ANY
# from fastapi.testclient import TestClient
# current_dir = os.path.dirname(os.path.abspath(__file__))
# backend_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
# if backend_root not in sys.path:
#     sys.path.append(backend_root)
# from main import app
# from legacy.interview_state import InterviewState, INTERVIEW_CATEGORIES

# client = TestClient(app)

# # ==========================================
# # FIXTURES
# # ==========================================

# @pytest.fixture
# def sample_start_payload():
#     return {"session_id": "session-123", "prompt": "How do I optimize AAV yield in HEK293 cells?"}


# @pytest.fixture
# def sample_answer_payload():
#     return {"session_id": "session-123", "answer": "We utilize a triple-transfection method."}


# ==========================================
# /interview/start ENDPOINT TESTS
# ==========================================

# @patch("legacy.interview_state.save_interview_state")
# @patch("legacy.interview_state.generate_interview_question")
# def test_start_success(mock_gen_question, mock_save_state, sample_start_payload):
#     mock_gen_question.return_value = "What cell line are you using?"
    
#     response = client.post("/interview/start", json=sample_start_payload)
    
#     assert response.status_code == 200
#     data = response.json()
#     assert data["question"] == "What cell line are you using?"
#     assert data["progress"] == "Question 1 of 5"
#     assert data["progress_ratio"] == "0/5"
#     assert data["complete"] is False
    
#     # Assert specific parameters passed to collaborators
#     mock_gen_question.assert_called_once()
#     actual_state_passed = mock_gen_question.call_args[0][0]
#     assert isinstance(actual_state_passed, InterviewState)
#     assert actual_state_passed.original_question == sample_start_payload["prompt"]
#     assert actual_state_passed.active is True
    
#     mock_save_state.assert_called_once_with(sample_start_payload["session_id"], actual_state_passed)


# @patch("legacy.interview_state.generate_interview_question")
# def test_start_question_generation_failure(mock_gen_question, sample_start_payload):
#     mock_gen_question.side_effect = RuntimeError("LLM connection timed out")
    
#     with pytest.raises(RuntimeError, match="LLM connection timed out"):
#         client.post("/interview/start", json=sample_start_payload)


# ==========================================
# /interview/answer ENDPOINT TESTS
# ==========================================

# @patch("legacy.interview_state.load_interview_state")
# def test_answer_no_state_returns_404(mock_load_state, sample_answer_payload):
#     mock_load_state.return_value = None
    
#     response = client.post("/interview/answer", json=sample_answer_payload)
    
#     assert response.status_code == 404
#     assert response.json()["detail"] == "No active interview for this session"
#     mock_load_state.assert_called_once_with(sample_answer_payload["session_id"])


# @patch("legacy.interview_state.save_interview_state")
# @patch("legacy.interview_state.generate_interview_question")
# @patch("legacy.interview_state.load_interview_state")
# def test_answer_progresses_interview(mock_load_state, mock_gen_question, mock_save_state, sample_answer_payload):
#     state = InterviewState()
#     state.active = True
#     state.record_question(INTERVIEW_CATEGORIES[0], "Initial question?")
#     mock_load_state.return_value = state
#     mock_gen_question.return_value = "Next topic question?"
    
#     response = client.post("/interview/answer", json=sample_answer_payload)
    
#     assert response.status_code == 200
#     data = response.json()
#     assert data["complete"] is False
#     assert data["question"] == "Next topic question?"
#     assert data["progress"] == "Question 2 of 5"
    
#     # Assert internal argument validation
#     mock_gen_question.assert_called_once_with(state, INTERVIEW_CATEGORIES[1])
#     mock_save_state.assert_called_once_with(sample_answer_payload["session_id"], state)


# @patch("legacy.interview_state.save_interview_state")
# @patch("legacy.interview_state.load_interview_state")
# def test_answer_completes_interview(mock_load_state, mock_save_state, sample_answer_payload):
#     state = InterviewState()
#     state.active = True
#     for cat in INTERVIEW_CATEGORIES:
#         state.record_question(cat, f"Q {cat}")
#     for cat in INTERVIEW_CATEGORIES[:-1]:
#         state.record_answer(cat, "Prior answers")
#     mock_load_state.return_value = state
    
#     response = client.post("/interview/answer", json=sample_answer_payload)
    
#     assert response.status_code == 200
#     data = response.json()
#     assert data["complete"] is True
#     assert data["question"] == "Interview complete. Generating report..."
#     assert state.complete is True
#     mock_save_state.assert_called_once_with(sample_answer_payload["session_id"], state)


# ==========================================
# /interview/report ENDPOINT TESTS
# ==========================================

# @patch("legacy.interview_state.load_interview_state")
# def test_generate_report_no_state(mock_load_state, sample_answer_payload):
#     mock_load_state.return_value = None
    
#     response = client.post("/interview/report", json=sample_answer_payload)
    
#     assert response.status_code == 404
#     assert response.json()["detail"] == "No interview state found"
#     mock_load_state.assert_called_once_with(sample_answer_payload["session_id"])


# @patch("legacy.interview_state.save_interview_state")
# @patch("legacy.interview_state.experiment_design_query")
# @patch("legacy.interview_state.load_interview_state")
# def test_generate_report_success(mock_load_state, mock_query, mock_save_state, sample_answer_payload):
#     state = InterviewState()
#     mock_load_state.return_value = state
#     mock_query.return_value = {"summary": "Optimized parameters found.", "score": 90}
    
#     response = client.post("/interview/report", json=sample_answer_payload)
    
#     assert response.status_code == 200
#     assert response.json() == {"summary": "Optimized parameters found.", "score": 90}
#     mock_query.assert_called_once_with(state=state)
    
#     mock_save_state.assert_called_once()
#     args = mock_save_state.call_args[0]
#     assert args[0] == sample_answer_payload["session_id"]
#     assert isinstance(args[1], InterviewState)
#     assert args[1].active is False


# @patch("legacy.interview_state.experiment_design_query")
# @patch("legacy.interview_state.load_interview_state")
# def test_generate_report_query_failure(mock_load_state, mock_query, sample_answer_payload):
#     mock_load_state.return_value = InterviewState()
#     mock_query.side_effect = RuntimeError("Database timeout during RAG retrieval")
    
#     with pytest.raises(RuntimeError, match="Database timeout during RAG retrieval"):
#         client.post("/interview/report", json=sample_answer_payload)


# ==========================================
# /interview/should-start & /interview/is-greeting TESTS
# ==========================================

# @patch("legacy.interview_state.should_start_interview")
# @patch("legacy.interview_state.load_interview_state")
# @patch("legacy.interview_state.read_history")
# def test_should_start_endpoint(mock_read_history, mock_load_state, mock_should_start, sample_start_payload):
#     mock_read_history.return_value = ["prior context"]
#     state = InterviewState()
#     mock_load_state.return_value = state
#     mock_should_start.return_value = True
    
#     response = client.post("/interview/should-start", json=sample_start_payload)
    
#     assert response.status_code == 200
#     assert response.json() == {"should_start": True}
#     mock_read_history.assert_called_once_with(sample_start_payload["session_id"])
#     mock_should_start.assert_called_once_with(sample_start_payload["prompt"], state, ["prior context"])


# @patch("legacy.interview_state.is_greeting_or_formality")
# def test_is_greeting_endpoint(mock_is_greeting, sample_start_payload):
    mock_is_greeting.return_value = True
    
    response = client.post("/interview/is-greeting", json=sample_start_payload)
    
    assert response.status_code == 200
    assert response.json() == {"is_greeting": True}
    mock_is_greeting.assert_called_once_with(sample_start_payload["prompt"])