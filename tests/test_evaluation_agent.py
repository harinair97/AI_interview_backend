from app.agents.evaluation_agent import evaluation_agent
from app.agents.schemas import (
    Difficulty,
    EvaluationInput,
    EvaluationRecommendation,
    PlannedQuestion,
)


QUESTION = PlannedQuestion(
    id="technical-1",
    topic="API design",
    competency="API design",
    objective="Assess API design.",
    difficulty=Difficulty.MEDIUM,
)


def test_evaluator_requests_clarification_for_very_short_answer() -> None:
    result = evaluation_agent.invoke(
        EvaluationInput(question=QUESTION, candidate_answer="I used caching.")
    )

    assert result.recommended_action is EvaluationRecommendation.CLARIFY


def test_evaluator_moves_on_for_detailed_answer() -> None:
    answer = "word " * 40
    result = evaluation_agent.invoke(EvaluationInput(question=QUESTION, candidate_answer=answer))

    assert result.recommended_action is EvaluationRecommendation.MOVE_ON
