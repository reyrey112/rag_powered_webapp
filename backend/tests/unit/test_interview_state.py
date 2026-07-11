import sys
import os
import pytest
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
if backend_root not in sys.path:
    sys.path.append(backend_root)
from backend.legacy.interview_state import (
    InterviewState,
    INTERVIEW_CATEGORIES,
    SKIP_COMMANDS,
    is_skip_command,
    should_start_interview,
)

# ==========================================
# FIXTURES
# ==========================================

@pytest.fixture
def fresh_state():
    return InterviewState()


@pytest.fixture
def active_state():
    state = InterviewState()
    state.original_question = "How do I optimize AAV yield in HEK293 cells?"
    state.active = True
    return state


@pytest.fixture
def partial_state():
    state = InterviewState()
    state.original_question = "How do I optimize AAV yield in HEK293 cells?"
    state.active = True
    for category in INTERVIEW_CATEGORIES[:3]:
        state.record_question(category, f"Question about {category}?")
        state.record_answer(category, f"Answer about {category}")
    return state


@pytest.fixture
def complete_state():
    state = InterviewState()
    state.original_question = "How do I optimize AAV yield in HEK293 cells?"
    state.active = True
    for category in INTERVIEW_CATEGORIES:
        state.record_question(category, f"Question about {category}?")
        state.record_answer(category, f"Answer about {category}")
    return state


# ==========================================
# EXHAUSTIVE DOMAIN TEST SUITE
# ==========================================

class TestInterviewStateInit:

    def test_fresh_state_defaults(self, fresh_state):
        assert fresh_state.original_question == ""
        assert fresh_state.asked_categories == []
        assert fresh_state.questions_asked == {}
        assert fresh_state.answers == {}
        assert fresh_state.complete is False
        assert fresh_state.active is False
        assert fresh_state.report_generated is False

    def test_fresh_state_instances_are_independent(self):
        a = InterviewState()
        b = InterviewState()
        a.asked_categories.append("system")
        assert "system" not in b.asked_categories
        a.answers["system"] = "HEK293"
        assert "system" not in b.answers


class TestRecordQuestionAndAnswer:

    def test_record_question_adds_to_asked_categories(self, fresh_state):
        fresh_state.record_question("system", "What cell line are you using?")
        assert "system" in fresh_state.asked_categories

    def test_record_question_stores_text(self, fresh_state):
        fresh_state.record_question("system", "What cell line are you using?")
        assert fresh_state.questions_asked["system"] == "What cell line are you using?"

    def test_record_question_does_not_duplicate_category(self, fresh_state):
        fresh_state.record_question("system", "What cell line are you using?")
        fresh_state.record_question("system", "Asked again?")
        assert fresh_state.asked_categories.count("system") == 1

    def test_record_question_updates_text_on_duplicate(self, fresh_state):
        fresh_state.record_question("system", "First question")
        fresh_state.record_question("system", "Updated question")
        assert fresh_state.questions_asked["system"] == "Updated question"

    def test_record_answer_stores_answer(self, fresh_state):
        fresh_state.record_answer("system", "HEK293T cells")
        assert fresh_state.answers["system"] == "HEK293T cells"

    def test_record_answer_overwrites_existing(self, fresh_state):
        fresh_state.record_answer("system", "First answer")
        fresh_state.record_answer("system", "Updated answer")
        assert fresh_state.answers["system"] == "Updated answer"


class TestNextCategory:

    def test_returns_first_category_when_none_asked(self, fresh_state):
        assert fresh_state.next_category() == INTERVIEW_CATEGORIES[0]

    def test_returns_next_unanswered_category(self, active_state):
        active_state.record_question(INTERVIEW_CATEGORIES[0], "Q?")
        assert active_state.next_category() == INTERVIEW_CATEGORIES[1]

    def test_returns_none_when_all_asked(self, fresh_state):
        for category in INTERVIEW_CATEGORIES:
            fresh_state.record_question(category, "Q?")
        assert fresh_state.next_category() is None

    def test_respects_category_order(self, fresh_state):
        for i, category in enumerate(INTERVIEW_CATEGORIES):
            assert fresh_state.next_category() == INTERVIEW_CATEGORIES[i]
            fresh_state.record_question(category, "Q?")


class TestIsComplete:

    def test_not_complete_when_fresh(self, fresh_state):
        assert fresh_state.is_complete() is False

    def test_not_complete_with_partial_answers(self, partial_state):
        assert partial_state.is_complete() is False

    def test_complete_when_all_answered(self, complete_state):
        assert complete_state.is_complete() is True

    def test_sets_complete_flag_as_side_effect(self, complete_state):
        complete_state.is_complete()
        assert complete_state.complete is True

    def test_does_not_set_complete_flag_when_partial(self, partial_state):
        partial_state.is_complete()
        assert partial_state.complete is False


class TestCounts:

    def test_answered_count_zero_when_fresh(self, fresh_state):
        assert fresh_state.answered_count() == 0

    def test_answered_count_matches_answers(self, partial_state):
        assert partial_state.answered_count() == 3

    def test_answered_count_five_when_complete(self, complete_state):
        assert complete_state.answered_count() == 5

    def test_total_questions_always_five(self, fresh_state):
        assert fresh_state.total_questions() == len(INTERVIEW_CATEGORIES)


class TestProgressLabel:

    def test_progress_label_fresh(self, fresh_state):
        assert fresh_state.progress_label() == "Question 1 of 5"

    def test_progress_label_after_one_answer(self, active_state):
        active_state.record_answer(INTERVIEW_CATEGORIES[0], "HEK293T")
        assert active_state.progress_label() == "Question 2 of 5"

    def test_progress_label_complete(self, complete_state):
        assert complete_state.progress_label() == "Question 6 of 5"

    def test_progress_label_format(self, fresh_state):
        label = fresh_state.progress_label()
        parts = label.split(" ")
        assert parts[0] == "Question"
        assert parts[2] == "of"
        assert parts[1].isdigit()
        assert parts[3].isdigit()


class TestSerialization:

    def test_to_dict_contains_all_keys(self, active_state):
        d = active_state.to_dict()
        expected_keys = {
            "original_question", "asked_categories", "questions_asked",
            "answers", "complete", "active", "report_generated",
        }
        assert set(d.keys()) == expected_keys

    def test_roundtrip_fresh_state(self, fresh_state):
        restored = InterviewState.from_dict(fresh_state.to_dict())
        assert restored.original_question == fresh_state.original_question
        assert restored.active == fresh_state.active
        assert restored.complete == fresh_state.complete

    def test_roundtrip_partial_state(self, partial_state):
        restored = InterviewState.from_dict(partial_state.to_dict())
        assert restored.answers == partial_state.answers
        assert restored.asked_categories == partial_state.asked_categories

    def test_from_dict_handles_missing_keys_gracefully(self):
        restored = InterviewState.from_dict({})
        assert restored.original_question == ""
        assert restored.active is False
        assert restored.answers == {}

    # def test_nested_serialization_immutability(self, active_state):
    #     d = active_state.to_dict()
    #     d["asked_categories"].append("injected")
    #     assert "injected" not in active_state.asked_categories

    # def test_from_dict_values_are_copies(self, partial_state):
    #     d = partial_state.to_dict()
    #     restored = InterviewState.from_dict(d)
    #     restored.answers["new_key"] = "new_value"
    #     assert "new_key" not in d["answers"]


class TestSummary:

    def test_summary_includes_original_question(self, complete_state):
        summary = complete_state.summary()
        assert complete_state.original_question in summary

    def test_summary_includes_all_answers(self, complete_state):
        summary = complete_state.summary()
        for category in INTERVIEW_CATEGORIES:
            assert complete_state.answers[category] in summary

    def test_summary_excludes_unanswered_categories(self, partial_state):
        summary = partial_state.summary()
        unanswered = INTERVIEW_CATEGORIES[3:]
        for category in unanswered:
            assert f"Answer about {category}" not in summary

    def test_summary_empty_when_no_answers(self, fresh_state):
        fresh_state.original_question = "Test question"
        summary = fresh_state.summary()
        assert "Test question" in summary
        assert len(summary.strip().splitlines()) == 1


# class TestIsGreetingOrFormality:

    

    # def test_short_message_with_question_mark_not_greeting(self):
    #     assert is_greeting_or_formality("why?") is False


class TestIsSkipCommand:

    @pytest.mark.parametrize("message", sorted(SKIP_COMMANDS))
    def test_all_skip_commands_detected(self, message):
        assert is_skip_command(message) is True

    @pytest.mark.parametrize("message", ["skip", "  CONTINUE  ", "proceed"])
    def test_skip_commands_case_and_whitespace(self, message):
        assert is_skip_command(message) is True

    def test_partial_skip_phrases_not_detected(self):
        assert is_skip_command("please skip the next question") is False


class TestShouldStartInterview:

    def test_returns_false_when_interview_already_active(self, active_state):
        assert should_start_interview("Valid research length question context", active_state, []) is False

    @pytest.mark.parametrize(
        "prompt, expected",
        [
            ("a" * 19, False),
            ("a" * 20, True),
            ("a" * 21, True),
        ]
    )
    def test_length_boundaries(self, prompt, expected, fresh_state):
        assert should_start_interview(prompt, fresh_state, []) is expected

    # def test_history_containing_only_greetings(self, fresh_state):
    #     history = ["Hello", "Hi there", "Good morning"]
    #     assert should_start_interview("How do I optimize cell cultures?", fresh_state, history) is True


# ==========================================
# STEP LIFECYCLE PROGRESSION TEST
# ==========================================

def test_full_interview_state_lifecycle_progression():
    state = InterviewState()
    assert state.is_complete() is False
    assert state.answered_count() == 0
    
    while not state.is_complete():
        category = state.next_category()
        assert category is not None
        state.record_question(category, f"Question text for {category}")
        state.record_answer(category, f"Answer text for {category}")
        
    assert state.is_complete() is True
    assert state.next_category() is None
    assert state.answered_count() == 5
    assert state.total_questions() == 5