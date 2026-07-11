from app.agents.schemas import OrchestratorAction, OrchestratorDecision
from app.orchestration.fallback_policy import fallback_decision
from app.orchestration.interview_state import InterviewState


def _move_to_next_question(reason: str, state: InterviewState) -> OrchestratorDecision:
    return OrchestratorDecision(
        action=OrchestratorAction.MOVE_TO_NEXT_QUESTION,
        reason=reason,
        difficulty=state.get("current_difficulty"),
        confidence=1.0,
    )


def validate_orchestrator_action(
    decision: OrchestratorDecision,
    state: InterviewState,
) -> OrchestratorDecision:
    """Enforce hard interview limits and replace unsafe recommendations."""

    minimum_confidence = state.get("minimum_orchestrator_confidence", 0.6)
    if decision.confidence < minimum_confidence:
        return fallback_decision(state.get("evaluation"), state)

    available_topics = state.get("available_topics", [])
    if decision.target_topic and available_topics and decision.target_topic not in available_topics:
        return fallback_decision(state.get("evaluation"), state)

    if decision.action is OrchestratorAction.ASK_FOLLOW_UP:
        if state.get("follow_up_count", 0) >= state.get("max_follow_ups", 2):
            return _move_to_next_question("Maximum follow-up limit reached.", state)

    if decision.action is OrchestratorAction.ASK_CLARIFICATION:
        if state.get("clarification_count", 0) >= state.get("max_clarifications", 1):
            return _move_to_next_question("Maximum clarification limit reached.", state)

    if decision.action is OrchestratorAction.MOVE_TO_NEXT_SECTION:
        if state.get("remaining_questions_in_section", 0) > 0:
            return _move_to_next_question(
                "Required questions remain in the current section.", state
            )

        remaining_sections = state.get("remaining_sections", [])
        if not remaining_sections:
            return fallback_decision(state.get("evaluation"), state)

        if decision.next_section not in remaining_sections:
            return OrchestratorDecision(
                action=OrchestratorAction.MOVE_TO_NEXT_SECTION,
                reason="The requested section was unavailable; using the next planned section.",
                next_section=remaining_sections[0],
                confidence=1.0,
            )

    if decision.action is OrchestratorAction.ADJUST_DIFFICULTY:
        if decision.difficulty is None or state.get("difficulty_signal_streak", 0) < 2:
            return _move_to_next_question(
                "Difficulty changes require consistent evidence across two questions.", state
            )

    if decision.action is OrchestratorAction.END_INTERVIEW:
        if state.get("questions_answered", 0) < state.get("minimum_questions", 1):
            fallback = fallback_decision(state.get("evaluation"), state)
            if fallback.action is OrchestratorAction.END_INTERVIEW:
                return _move_to_next_question(
                    "Minimum interview coverage has not been reached.", state
                )
            return fallback

    return decision
