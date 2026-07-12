import json
import logging

from app.agents.schemas import (
    EvaluationInput,
    EvaluationRecommendation,
    EvaluationResult,
)
from app.agents.openai_client import StructuredOutputClient, create_openai_client
from app.config import get_settings
from app.prompts import load_prompt

logger = logging.getLogger(__name__)


class EvaluationAgent:
    """Structured LLM evaluator with a deterministic safety fallback."""

    def __init__(
        self,
        client: StructuredOutputClient | None = None,
        model: str | None = None,
    ) -> None:
        self.client = client
        self.model = model or get_settings().openai_evaluation_model

    def invoke(self, agent_input: EvaluationInput) -> EvaluationResult:
        if self.client is not None:
            try:
                return self.client.parse(
                    model=self.model,
                    instructions=load_prompt("evaluator.txt"),
                    input_text=json.dumps(agent_input.model_dump(mode="json")),
                    response_model=EvaluationResult,
                )
            except Exception as exc:
                logger.warning(
                    "Evaluation model failed; using deterministic fallback. error_type=%s",
                    type(exc).__name__,
                )

        return self._deterministic_evaluation(agent_input)

    @staticmethod
    def _deterministic_evaluation(agent_input: EvaluationInput) -> EvaluationResult:
        word_count = len(agent_input.candidate_answer.split())

        if word_count < 8:
            return EvaluationResult(
                correctness=2,
                depth=1,
                communication=2,
                missing_concepts=["sufficient detail"],
                recommended_action=EvaluationRecommendation.CLARIFY,
                follow_up_goal="Ask the candidate to make the answer more specific.",
            )

        if word_count < 35:
            return EvaluationResult(
                correctness=3,
                depth=2,
                communication=3,
                missing_concepts=["concrete example", "trade-offs"],
                recommended_action=EvaluationRecommendation.FOLLOW_UP,
                follow_up_goal=(
                    f"Collect a concrete example and trade-offs related to "
                    f"{agent_input.question.topic}."
                ),
            )

        return EvaluationResult(
            correctness=4,
            depth=4,
            communication=4,
            missing_concepts=[],
            recommended_action=EvaluationRecommendation.MOVE_ON,
        )


evaluation_agent = EvaluationAgent(client=create_openai_client())
