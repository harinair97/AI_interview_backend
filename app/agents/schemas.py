from enum import Enum

from pydantic import BaseModel, Field, model_validator


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


class PlannerInput(BaseModel):
    goal: InterviewGoal
    job_description: str | None = Field(default=None, max_length=20_000)
    candidate_summary: str | None = Field(default=None, max_length=10_000)
    requested_competencies: list[str] = Field(default_factory=list, max_length=12)

    @model_validator(mode="after")
    def normalize_competencies(self) -> "PlannerInput":
        normalized = list(
            dict.fromkeys(item.strip() for item in self.requested_competencies if item.strip())
        )
        self.requested_competencies = normalized
        return self


class PlannedQuestion(BaseModel):
    id: str = Field(min_length=1)
    topic: str = Field(min_length=1)
    competency: str = Field(min_length=1)
    objective: str = Field(min_length=1)
    difficulty: Difficulty
    required: bool = True


class InterviewSection(BaseModel):
    name: str = Field(min_length=1)
    order: int = Field(ge=0)
    questions: list[PlannedQuestion] = Field(min_length=1)


class InterviewPlan(BaseModel):
    goal: InterviewGoal
    competencies: list[CompetencyCoverage] = Field(min_length=1)
    sections: list[InterviewSection] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_plan(self) -> "InterviewPlan":
        ordered_sections = sorted(self.sections, key=lambda section: section.order)
        if ordered_sections != self.sections:
            raise ValueError("Interview sections must be ordered by their order field.")

        questions = [question for section in self.sections for question in section.questions]
        if len(questions) != self.goal.planned_question_count:
            raise ValueError("Plan question count must match the interview goal.")

        question_ids = [question.id for question in questions]
        if len(question_ids) != len(set(question_ids)):
            raise ValueError("Planned question IDs must be unique.")
        return self


class EvaluationResult(BaseModel):
    correctness: int = Field(ge=1, le=5)
    depth: int = Field(ge=1, le=5)
    communication: int = Field(ge=1, le=5)
    missing_concepts: list[str] = Field(default_factory=list)
    recommended_action: EvaluationRecommendation
    follow_up_goal: str | None = None


class EvaluationInput(BaseModel):
    question: PlannedQuestion
    candidate_answer: str = Field(min_length=1, max_length=20_000)


class SubmitAnswerResult(BaseModel):
    interview_id: str
    status: InterviewStatus
    evaluation: EvaluationResult
    decision: OrchestratorDecision
    interviewer_message: str
