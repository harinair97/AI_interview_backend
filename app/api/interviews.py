from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.agents.schemas import (
    Difficulty,
    InterviewGoal,
    InterviewPlan,
    OrchestratorDecision,
    PlannerInput,
)
from app.orchestration.workflow_engine import interview_graph

router = APIRouter(prefix="/interviews", tags=["interviews"])


class CreateInterviewRequest(BaseModel):
    target_role: str = Field(min_length=1)
    difficulty: Difficulty = Difficulty.MEDIUM
    planned_question_count: int = Field(default=8, ge=1, le=30)
    job_description: str | None = Field(default=None, max_length=20_000)
    candidate_summary: str | None = Field(default=None, max_length=10_000)
    competencies: list[str] = Field(default_factory=list, max_length=12)


class CreateInterviewResponse(BaseModel):
    interview_id: str
    status: str
    interviewer_message: str
    decision: OrchestratorDecision
    plan: InterviewPlan
    events: list[str]


@router.post("", response_model=CreateInterviewResponse, status_code=201)
def create_interview(request: CreateInterviewRequest) -> CreateInterviewResponse:
    result = interview_graph.invoke(
        {
            "planner_input": PlannerInput(
                goal=InterviewGoal(
                    target_role=request.target_role,
                    difficulty=request.difficulty,
                    planned_question_count=request.planned_question_count,
                ),
                job_description=request.job_description,
                candidate_summary=request.candidate_summary,
                requested_competencies=request.competencies,
            )
        }
    )
    return CreateInterviewResponse.model_validate(result)


@router.post("/demo", response_model=CreateInterviewResponse)
def start_demo_interview() -> CreateInterviewResponse:
    request = CreateInterviewRequest(target_role="Backend Software Engineer")
    return create_interview(request)
