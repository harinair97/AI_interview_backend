from app.agents.schemas import (
    EvaluationRecommendation,
    EvaluationResult,
    OrchestratorAction,
    OrchestratorDecision,
)
from app.orchestration.interview_state import InterviewState


def fallback_decision(
    evaluation: EvaluationResult | None,
    state: InterviewState,
) -> OrchestratorDecision:
    """Choose a safe action without relying on an orchestrator model."""

    if (
        evaluation is not None
        and evaluation.recommended_action is EvaluationRecommendation.FOLLOW_UP
        and state.get("follow_up_count", 0) < state.get("max_follow_ups", 2)
    ):
        return OrchestratorDecision(
            action=OrchestratorAction.ASK_FOLLOW_UP,
            reason="Fallback based on the evaluator recommendation.",
            interviewer_goal=evaluation.follow_up_goal,
            difficulty=state.get("current_difficulty"),
            confidence=1.0,
        )

    if state.get("remaining_questions_in_section", 0) > 0:
        return OrchestratorDecision(
            action=OrchestratorAction.MOVE_TO_NEXT_QUESTION,
            reason="Fallback to the next planned question in the current section.",
            difficulty=state.get("current_difficulty"),
            confidence=1.0,
        )

    remaining_sections = state.get("remaining_sections", [])
    if remaining_sections:
        return OrchestratorDecision(
            action=OrchestratorAction.MOVE_TO_NEXT_SECTION,
            reason="Fallback to the next planned interview section.",
            next_section=remaining_sections[0],
            confidence=1.0,
        )

    return OrchestratorDecision(
        action=OrchestratorAction.END_INTERVIEW,
        reason="All planned interview sections are complete.",
        confidence=1.0,
    )
