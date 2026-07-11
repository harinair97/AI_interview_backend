from typing import TypedDict

from app.agents.schemas import InterviewGoal, OrchestratorDecision


class InterviewState(TypedDict, total=False):
    """Shared LangGraph state; nodes return partial updates to this structure."""

    interview_id: str
    goal: InterviewGoal
    status: str
    current_section: str
    question_index: int
    questions_answered: int
    follow_up_count: int
    max_follow_ups: int
    minimum_questions: int
    candidate_answer: str
    decision: OrchestratorDecision
    interviewer_message: str
    events: list[str]

