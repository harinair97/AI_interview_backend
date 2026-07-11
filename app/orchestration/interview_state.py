from typing import TypedDict

from app.agents.schemas import (
    CompetencyCoverage,
    Difficulty,
    EvaluationResult,
    InterviewGoal,
    InterviewStatus,
    OrchestratorDecision,
)


class InterviewState(TypedDict, total=False):
    """Shared LangGraph state; nodes return partial updates to this structure."""

    interview_id: str
    goal: InterviewGoal
    status: InterviewStatus
    current_section: str
    question_index: int
    questions_answered: int
    follow_up_count: int
    max_follow_ups: int
    clarification_count: int
    max_clarifications: int
    minimum_questions: int
    remaining_questions_in_section: int
    remaining_sections: list[str]
    available_topics: list[str]
    coverage: list[CompetencyCoverage]
    current_difficulty: Difficulty
    difficulty_signal_streak: int
    minimum_orchestrator_confidence: float
    candidate_answer: str
    evaluation: EvaluationResult
    decision: OrchestratorDecision
    interviewer_message: str
    events: list[str]
