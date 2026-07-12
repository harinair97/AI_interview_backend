import json
import logging

from app.agents.openai_client import StructuredOutputClient, create_openai_client
from app.agents.schemas import (
    EvaluationRecommendation,
    OrchestratorAction,
    OrchestratorDecision,
)
from app.config import get_settings
from app.orchestration.context_builder import build_orchestrator_context
from app.orchestration.interview_state import InterviewState
from app.prompts import load_prompt

logger = logging.getLogger(__name__)


class OrchestratorAgent:
    """Structured LLM director with deterministic recommendation fallback."""

    def __init__(
        self,
        client: StructuredOutputClient | None = None,
        model: str | None = None,
    ) -> None:
        self.client = client
        self.model = model or get_settings().openai_orchestrator_model

    def invoke(self, state: InterviewState) -> OrchestratorDecision:
        if self.client is not None:
            try:
                context = build_orchestrator_context(state)
                return self.client.parse(
                    model=self.model,
                    instructions=load_prompt("orchestrator.txt"),
                    input_text=json.dumps(context),
                    response_model=OrchestratorDecision,
                )
            except Exception as exc:
                logger.warning(
                    "Orchestrator model failed; using deterministic fallback. error_type=%s",
                    type(exc).__name__,
                )

        return self._deterministic_decision(state)

    @staticmethod
    def _deterministic_decision(state: InterviewState) -> OrchestratorDecision:
        evaluation = state["evaluation"]
        current_question = _question_at(state, state["question_index"])

        if evaluation.recommended_action is EvaluationRecommendation.CLARIFY:
            return OrchestratorDecision(
                action=OrchestratorAction.ASK_CLARIFICATION,
                reason="The answer is too brief to evaluate reliably.",
                target_topic=current_question.topic,
                interviewer_goal=evaluation.follow_up_goal,
                difficulty=state["current_difficulty"],
                confidence=0.95,
            )

        if evaluation.recommended_action is EvaluationRecommendation.FOLLOW_UP:
            return OrchestratorDecision(
                action=OrchestratorAction.ASK_FOLLOW_UP,
                reason="The answer is relevant but needs concrete evidence and trade-offs.",
                target_topic=current_question.topic,
                interviewer_goal=evaluation.follow_up_goal,
                difficulty=state["current_difficulty"],
                confidence=0.9,
            )

        next_index = state["question_index"] + 1
        questions = _all_questions(state)
        if next_index < len(questions):
            next_question = questions[next_index]
            return OrchestratorDecision(
                action=OrchestratorAction.MOVE_TO_NEXT_QUESTION,
                reason="The current answer provides sufficient evidence to move on.",
                target_topic=next_question.topic,
                interviewer_goal=next_question.objective,
                difficulty=next_question.difficulty,
                confidence=0.95,
            )

        return OrchestratorDecision(
            action=OrchestratorAction.END_INTERVIEW,
            reason="The candidate answered the final planned question.",
            confidence=0.95,
        )


def _all_questions(state: InterviewState):
    return [question for section in state["plan"].sections for question in section.questions]


def _question_at(state: InterviewState, index: int):
    return _all_questions(state)[index]


orchestrator_agent = OrchestratorAgent(client=create_openai_client())
