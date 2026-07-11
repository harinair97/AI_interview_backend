from fastapi import APIRouter
from pydantic import BaseModel

from app.agents.schemas import Difficulty, InterviewGoal, OrchestratorDecision
from app.orchestration.workflow_engine import interview_graph

router = APIRouter(prefix="/interviews", tags=["interviews"])


class DemoInterviewResponse(BaseModel):
    interview_id: str
    status: str
    interviewer_message: str
    decision: OrchestratorDecision
    events: list[str]


@router.post("/demo", response_model=DemoInterviewResponse)
def start_demo_interview() -> DemoInterviewResponse:
    result = interview_graph.invoke(
        {
            "goal": InterviewGoal(
                target_role="Backend Software Engineer",
                difficulty=Difficulty.MEDIUM,
                planned_question_count=8,
            )
        }
    )
    return DemoInterviewResponse.model_validate(result)

