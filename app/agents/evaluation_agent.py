from app.agents.schemas import (
    EvaluationInput,
    EvaluationRecommendation,
    EvaluationResult,
)


class EvaluationAgent:
    """Deterministic evaluator used until a structured-output LLM is connected."""

    def invoke(self, agent_input: EvaluationInput) -> EvaluationResult:
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


evaluation_agent = EvaluationAgent()
