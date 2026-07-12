from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agents.schemas import (
    Difficulty,
    InterviewGoal,
    InterviewPlan,
    OrchestratorDecision,
    PlannerInput,
    SubmitAnswerResult,
)
from app.database import get_session
from app.services.interview_service import InterviewService

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


class InterviewEventResponse(BaseModel):
    sequence: int
    event_type: str
    payload: dict

    model_config = {"from_attributes": True}


class InterviewDetailResponse(BaseModel):
    interview_id: str
    status: str
    target_role: str
    goal: dict
    plan: InterviewPlan
    runtime_state: dict
    interviewer_message: str
    events: list[InterviewEventResponse]


class SubmitAnswerRequest(BaseModel):
    answer: str = Field(min_length=1, max_length=20_000)


@router.post("", response_model=CreateInterviewResponse, status_code=201)
def create_interview(
    request: CreateInterviewRequest,
    session: Annotated[Session, Depends(get_session)],
) -> CreateInterviewResponse:
    planner_input = PlannerInput(
        goal=InterviewGoal(
            target_role=request.target_role,
            difficulty=request.difficulty,
            planned_question_count=request.planned_question_count,
        ),
        job_description=request.job_description,
        candidate_summary=request.candidate_summary,
        requested_competencies=request.competencies,
    )
    result = InterviewService(session).create(planner_input)
    return CreateInterviewResponse.model_validate(result)


@router.get("/{interview_id}", response_model=InterviewDetailResponse)
def get_interview(
    interview_id: str,
    session: Annotated[Session, Depends(get_session)],
) -> InterviewDetailResponse:
    interview = InterviewService(session).get(interview_id)
    if interview is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found.",
        )
    return InterviewDetailResponse(
        interview_id=interview.id,
        status=interview.status,
        target_role=interview.target_role,
        goal=interview.goal,
        plan=interview.plan,
        runtime_state=interview.runtime_state,
        interviewer_message=interview.interviewer_message,
        events=[InterviewEventResponse.model_validate(event) for event in interview.events],
    )


@router.post("/{interview_id}/answers", response_model=SubmitAnswerResult)
def submit_answer(
    interview_id: str,
    request: SubmitAnswerRequest,
    session: Annotated[Session, Depends(get_session)],
) -> SubmitAnswerResult:
    service = InterviewService(session)
    interview = service.get(interview_id)
    if interview is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found.",
        )
    try:
        return service.submit_answer(interview, request.answer)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.post("/demo", response_model=CreateInterviewResponse)
def start_demo_interview(
    session: Annotated[Session, Depends(get_session)],
) -> CreateInterviewResponse:
    request = CreateInterviewRequest(target_role="Backend Software Engineer")
    return create_interview(request, session)
