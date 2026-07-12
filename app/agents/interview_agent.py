import json
import logging

from app.agents.openai_client import StructuredOutputClient, create_openai_client
from app.agents.schemas import InterviewerOutput, OrchestratorAction
from app.config import get_settings
from app.orchestration.context_builder import build_interviewer_context
from app.orchestration.interview_state import InterviewState
from app.prompts import load_prompt

logger = logging.getLogger(__name__)


class InterviewAgent:
    """Generate candidate-facing language with a deterministic safety fallback."""

    def __init__(
        self,
        client: StructuredOutputClient | None = None,
        model: str | None = None,
    ) -> None:
        self.client = client
        self.model = model or get_settings().openai_interview_model

    def invoke(self, state: InterviewState) -> str:
        if self.client is not None:
            try:
                output = self.client.parse(
                    model=self.model,
                    instructions=load_prompt("interviewer.txt"),
                    input_text=json.dumps(build_interviewer_context(state)),
                    response_model=InterviewerOutput,
                )
                return output.message
            except Exception as exc:
                logger.warning(
                    "Interview model failed; using deterministic fallback. error_type=%s",
                    type(exc).__name__,
                )

        return self._deterministic_message(state)

    @staticmethod
    def _deterministic_message(state: InterviewState) -> str:
        decision = state["decision"]

        if decision.action is OrchestratorAction.ASK_INITIAL_QUESTION:
            role = state["goal"].target_role
            return (
                "Welcome. To get started, could you briefly describe the experience "
                f"that best prepares you for a {role} role?"
            )

        if decision.action is OrchestratorAction.ASK_CLARIFICATION:
            return "Could you make that answer more specific and explain your reasoning?"

        if decision.action is OrchestratorAction.ASK_FOLLOW_UP:
            return (
                f"Could you give a concrete example involving {decision.target_topic} "
                "and explain the trade-offs you considered?"
            )

        if decision.action is OrchestratorAction.CHALLENGE_ANSWER:
            return (
                f"Let's examine {decision.target_topic} more closely. What limitations "
                "or failure cases might challenge your approach?"
            )

        if decision.action is OrchestratorAction.END_INTERVIEW:
            return "Thank you. That completes the planned interview."

        question = _current_question(state)
        return (
            f"Let's move to {question.topic}. {question.objective} "
            "How would you approach this in practice?"
        )


def _current_question(state: InterviewState):
    questions = [
        question for section in state["plan"].sections for question in section.questions
    ]
    return questions[state["question_index"]]


interview_agent = InterviewAgent(client=create_openai_client())
