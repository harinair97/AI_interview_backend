from app.agents.schemas import (
    Difficulty,
    EvaluationRecommendation,
    EvaluationResult,
    OrchestratorAction,
    OrchestratorDecision,
)
from app.orchestration.fallback_policy import fallback_decision
from app.orchestration.interview_state import InterviewState
from app.orchestration.policy_validator import validate_orchestrator_action


def make_state(**overrides) -> InterviewState:
    state: InterviewState = {
        "questions_answered": 2,
        "minimum_questions": 3,
        "follow_up_count": 0,
        "max_follow_ups": 2,
        "clarification_count": 0,
        "max_clarifications": 1,
        "remaining_questions_in_section": 2,
        "remaining_sections": ["behavioral"],
        "available_topics": ["api design", "databases"],
        "current_difficulty": Difficulty.MEDIUM,
        "difficulty_signal_streak": 0,
        "minimum_orchestrator_confidence": 0.6,
    }
    state.update(overrides)
    return state


def decision(action: OrchestratorAction, **overrides) -> OrchestratorDecision:
    data = {
        "action": action,
        "reason": "Model recommendation.",
        "confidence": 0.9,
    }
    data.update(overrides)
    return OrchestratorDecision(**data)


def test_follow_up_is_replaced_at_limit() -> None:
    state = make_state(follow_up_count=2)

    approved = validate_orchestrator_action(
        decision(OrchestratorAction.ASK_FOLLOW_UP), state
    )

    assert approved.action is OrchestratorAction.MOVE_TO_NEXT_QUESTION
    assert approved.reason == "Maximum follow-up limit reached."


def test_section_change_is_replaced_when_questions_remain() -> None:
    approved = validate_orchestrator_action(
        decision(OrchestratorAction.MOVE_TO_NEXT_SECTION, next_section="behavioral"),
        make_state(),
    )

    assert approved.action is OrchestratorAction.MOVE_TO_NEXT_QUESTION


def test_early_end_is_rejected_even_with_inconsistent_empty_plan() -> None:
    state = make_state(remaining_questions_in_section=0, remaining_sections=[])

    approved = validate_orchestrator_action(
        decision(OrchestratorAction.END_INTERVIEW), state
    )

    assert approved.action is OrchestratorAction.MOVE_TO_NEXT_QUESTION
    assert approved.reason == "Minimum interview coverage has not been reached."


def test_difficulty_change_requires_two_question_signal() -> None:
    approved = validate_orchestrator_action(
        decision(OrchestratorAction.ADJUST_DIFFICULTY, difficulty=Difficulty.HARD),
        make_state(difficulty_signal_streak=1),
    )

    assert approved.action is OrchestratorAction.MOVE_TO_NEXT_QUESTION


def test_low_confidence_uses_evaluator_fallback() -> None:
    evaluation = EvaluationResult(
        correctness=3,
        depth=2,
        communication=4,
        recommended_action=EvaluationRecommendation.FOLLOW_UP,
        follow_up_goal="Test cache invalidation trade-offs.",
    )
    state = make_state(evaluation=evaluation)

    approved = validate_orchestrator_action(
        decision(OrchestratorAction.END_INTERVIEW, confidence=0.2), state
    )

    assert approved.action is OrchestratorAction.ASK_FOLLOW_UP
    assert approved.interviewer_goal == "Test cache invalidation trade-offs."


def test_unavailable_topic_uses_safe_fallback() -> None:
    approved = validate_orchestrator_action(
        decision(
            OrchestratorAction.MOVE_TO_NEXT_QUESTION,
            target_topic="quantum computing",
        ),
        make_state(),
    )

    assert approved.action is OrchestratorAction.MOVE_TO_NEXT_QUESTION
    assert approved.target_topic is None
    assert approved.confidence == 1.0


def test_fallback_moves_through_questions_sections_then_ends() -> None:
    assert fallback_decision(None, make_state()).action is OrchestratorAction.MOVE_TO_NEXT_QUESTION
    assert (
        fallback_decision(None, make_state(remaining_questions_in_section=0)).action
        is OrchestratorAction.MOVE_TO_NEXT_SECTION
    )
    assert (
        fallback_decision(
            None,
            make_state(remaining_questions_in_section=0, remaining_sections=[]),
        ).action
        is OrchestratorAction.END_INTERVIEW
    )
