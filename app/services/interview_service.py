from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.agents.schemas import (
    InterviewGoal,
    InterviewPlan,
    InterviewStatus,
    PlannerInput,
    SubmitAnswerResult,
)
from app.models.interview import InterviewRecord
from app.orchestration.answer_workflow import answer_graph
from app.orchestration.workflow_engine import interview_graph
from app.repositories.interview_repository import InterviewRepository


class InterviewService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = InterviewRepository(session)

    def create(self, planner_input: PlannerInput) -> dict:
        result = interview_graph.invoke({"planner_input": planner_input})
        encoded = jsonable_encoder(result)
        interview = InterviewRecord(
            id=encoded["interview_id"],
            status=encoded["status"],
            target_role=encoded["goal"]["target_role"],
            goal=encoded["goal"],
            plan=encoded["plan"],
            runtime_state=self._runtime_state(encoded),
            interviewer_message=encoded["interviewer_message"],
        )

        try:
            self.repository.add(interview)
            self.repository.add_events(
                interview.id,
                [(event_type, {}) for event_type in encoded["events"]],
            )
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

        return result

    def get(self, interview_id: str) -> InterviewRecord | None:
        return self.repository.get(interview_id)

    def submit_answer(
        self,
        interview: InterviewRecord,
        candidate_answer: str,
    ) -> SubmitAnswerResult:
        if interview.status == InterviewStatus.COMPLETED.value:
            raise ValueError("The interview is already complete.")

        graph_input = {
            **interview.runtime_state,
            "interview_id": interview.id,
            "goal": InterviewGoal.model_validate(interview.goal),
            "plan": InterviewPlan.model_validate(interview.plan),
            "candidate_answer": candidate_answer,
        }
        result = answer_graph.invoke(graph_input)
        encoded = jsonable_encoder(result)

        interview.status = encoded["status"]
        interview.runtime_state = self._runtime_state(encoded)
        interview.interviewer_message = encoded["interviewer_message"]
        events = [
            ("CANDIDATE_ANSWER_SUBMITTED", {"answer": candidate_answer}),
            ("ANSWER_EVALUATED", encoded["evaluation"]),
            ("ORCHESTRATOR_DECISION_APPROVED", encoded["decision"]),
            (
                "INTERVIEWER_MESSAGE_CREATED",
                {"message": encoded["interviewer_message"]},
            ),
        ]

        try:
            self.repository.add_events(interview.id, events)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

        return SubmitAnswerResult.model_validate(encoded)

    @staticmethod
    def _runtime_state(encoded: dict) -> dict:
        excluded = {"planner_input", "goal", "plan", "interviewer_message", "events"}
        return {key: value for key, value in encoded.items() if key not in excluded}
