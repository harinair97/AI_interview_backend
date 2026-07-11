from enum import Enum

from pydantic import BaseModel, Field


class Difficulty(str, Enum):
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"


class InterviewStatus(str, Enum):
    PLANNING = "PLANNING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class CoverageStatus(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    PARTIAL = "PARTIAL"
    SUFFICIENT = "SUFFICIENT"


class EvaluationRecommendation(str, Enum):
    FOLLOW_UP = "FOLLOW_UP"
    CLARIFY = "CLARIFY"
    CHALLENGE = "CHALLENGE"
    MOVE_ON = "MOVE_ON"


class OrchestratorAction(str, Enum):
    ASK_INITIAL_QUESTION = "ASK_INITIAL_QUESTION"
    ASK_FOLLOW_UP = "ASK_FOLLOW_UP"
    ASK_CLARIFICATION = "ASK_CLARIFICATION"
    CHALLENGE_ANSWER = "CHALLENGE_ANSWER"
    MOVE_TO_NEXT_QUESTION = "MOVE_TO_NEXT_QUESTION"
    MOVE_TO_NEXT_SECTION = "MOVE_TO_NEXT_SECTION"
    ADJUST_DIFFICULTY = "ADJUST_DIFFICULTY"
    END_INTERVIEW = "END_INTERVIEW"


class OrchestratorDecision(BaseModel):
    action: OrchestratorAction
    reason: str = Field(min_length=1)
    target_topic: str | None = None
    interviewer_goal: str | None = None
    difficulty: Difficulty | None = None
    next_section: str | None = None
    confidence: float = Field(ge=0, le=1)


class InterviewGoal(BaseModel):
    target_role: str = Field(min_length=1)
    difficulty: Difficulty = Difficulty.MEDIUM
    planned_question_count: int = Field(default=8, ge=1, le=30)


class CompetencyCoverage(BaseModel):
    name: str = Field(min_length=1)
    importance: int = Field(default=3, ge=1, le=5)
    coverage: CoverageStatus = CoverageStatus.NOT_STARTED
    average_score: float | None = Field(default=None, ge=1, le=5)


class EvaluationResult(BaseModel):
    correctness: int = Field(ge=1, le=5)
    depth: int = Field(ge=1, le=5)
    communication: int = Field(ge=1, le=5)
    missing_concepts: list[str] = Field(default_factory=list)
    recommended_action: EvaluationRecommendation
    follow_up_goal: str | None = None
