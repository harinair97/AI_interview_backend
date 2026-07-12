from typing import Any

from pydantic import BaseModel

from app.agents.evaluation_agent import EvaluationAgent
from app.agents.interview_agent import InterviewAgent
from app.agents.orchestrator_agent import OrchestratorAgent
from app.agents.planner_agent import PlannerAgent
from app.agents.schemas import (
    CompetencyCoverage,
    Difficulty,
    EvaluationInput,
    EvaluationRecommendation,
    EvaluationResult,
    InterviewGoal,
    InterviewSection,
    InterviewerOutput,
    OrchestratorAction,
    OrchestratorDecision,
    PlannedQuestion,
    PlannerInput,
    PlannerOutput,
)
from app.orchestration.context_builder import (
    build_interviewer_context,
    build_orchestrator_context,
)
from app.orchestration.workflow_engine import interview_graph


class FakeStructuredClient:
    def __init__(self, result: BaseModel | None = None, error: Exception | None = None):
        self.result = result
        self.error = error
        self.calls: list[dict[str, Any]] = []

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.result


QUESTION = PlannedQuestion(
    id="technical-1",
    topic="API design",
    competency="API design",
    objective="Assess API design trade-offs.",
    difficulty=Difficulty.MEDIUM,
)


def test_evaluator_uses_structured_llm_result() -> None:
    expected = EvaluationResult(
        correctness=5,
        depth=4,
        communication=4,
        missing_concepts=["idempotency"],
        recommended_action=EvaluationRecommendation.FOLLOW_UP,
        follow_up_goal="Test idempotency handling.",
    )
    client = FakeStructuredClient(result=expected)

    result = EvaluationAgent(client=client, model="test-model").invoke(
        EvaluationInput(question=QUESTION, candidate_answer="A substantive candidate answer.")
    )

    assert result == expected
    assert client.calls[0]["model"] == "test-model"
    assert client.calls[0]["response_model"] is EvaluationResult


def test_planner_uses_llm_to_create_role_specific_sections() -> None:
    planner_input = PlannerInput(
        goal=InterviewGoal(target_role="Product Manager", planned_question_count=4),
        job_description="Own product discovery, prioritization, and cross-functional delivery.",
        requested_competencies=["product discovery", "prioritization", "stakeholder alignment"],
    )
    output = PlannerOutput(
        competencies=[
            CompetencyCoverage(name="product discovery", importance=5),
            CompetencyCoverage(name="prioritization", importance=5),
            CompetencyCoverage(name="stakeholder alignment", importance=4),
        ],
        sections=[
            InterviewSection(
                name="product background",
                order=0,
                questions=[
                    planned_question("product-background", "product discovery", "career context")
                ],
            ),
            InterviewSection(
                name="discovery and prioritization",
                order=1,
                questions=[
                    planned_question("discovery", "product discovery", "customer discovery"),
                    planned_question("prioritization", "prioritization", "roadmap trade-offs"),
                ],
            ),
            InterviewSection(
                name="cross-functional leadership",
                order=2,
                questions=[
                    planned_question(
                        "stakeholder-alignment",
                        "stakeholder alignment",
                        "conflicting stakeholders",
                    )
                ],
            ),
        ],
    )
    client = FakeStructuredClient(result=output)

    plan = PlannerAgent(client=client, model="test-model").invoke(planner_input)

    assert plan.goal == planner_input.goal
    assert [section.name for section in plan.sections] == [
        "product background",
        "discovery and prioritization",
        "cross-functional leadership",
    ]
    assert client.calls[0]["response_model"] is PlannerOutput
    assert "Product Manager" in client.calls[0]["input_text"]


def test_planner_falls_back_when_llm_plan_has_wrong_question_count() -> None:
    planner_input = PlannerInput(
        goal=InterviewGoal(target_role="Data Engineer", planned_question_count=4),
        requested_competencies=["SQL", "data modeling"],
    )
    invalid_output = PlannerOutput(
        competencies=[
            CompetencyCoverage(name="SQL"),
            CompetencyCoverage(name="data modeling"),
        ],
        sections=[
            InterviewSection(
                name="SQL",
                order=0,
                questions=[planned_question("sql", "SQL", "query design")],
            )
        ],
    )

    plan = PlannerAgent(client=FakeStructuredClient(result=invalid_output)).invoke(planner_input)

    assert [section.name for section in plan.sections] == [
        "introduction",
        "technical",
        "behavioral",
    ]
    assert sum(len(section.questions) for section in plan.sections) == 4


def test_planner_falls_back_when_requested_competency_is_omitted() -> None:
    planner_input = PlannerInput(
        goal=InterviewGoal(target_role="Designer", planned_question_count=1),
        requested_competencies=["user research"],
    )
    output = PlannerOutput(
        competencies=[CompetencyCoverage(name="visual design")],
        sections=[
            InterviewSection(
                name="portfolio",
                order=0,
                questions=[
                    planned_question("portfolio", "visual design", "portfolio evidence")
                ],
            )
        ],
    )

    plan = PlannerAgent(client=FakeStructuredClient(result=output)).invoke(planner_input)

    assert [competency.name for competency in plan.competencies] == ["user research"]


def test_evaluator_falls_back_when_provider_fails() -> None:
    client = FakeStructuredClient(error=TimeoutError("provider timeout"))

    result = EvaluationAgent(client=client).invoke(
        EvaluationInput(question=QUESTION, candidate_answer="Too short.")
    )

    assert result.recommended_action is EvaluationRecommendation.CLARIFY


def test_orchestrator_uses_compact_context_and_structured_result() -> None:
    state = make_answer_state()
    expected = OrchestratorDecision(
        action=OrchestratorAction.ASK_FOLLOW_UP,
        reason="The answer needs a concrete trade-off.",
        target_topic="candidate background",
        interviewer_goal="Collect one concrete trade-off.",
        difficulty=Difficulty.MEDIUM,
        confidence=0.9,
    )
    client = FakeStructuredClient(result=expected)

    result = OrchestratorAgent(client=client, model="test-model").invoke(state)

    assert result == expected
    input_text = client.calls[0]["input_text"]
    assert "candidate_answer" in input_text
    assert "planner_input" not in input_text
    assert "interviewer_message" not in input_text


def test_orchestrator_falls_back_when_structured_call_fails() -> None:
    state = make_answer_state()
    client = FakeStructuredClient(error=ValueError("invalid structured output"))

    result = OrchestratorAgent(client=client).invoke(state)

    assert result.action is OrchestratorAction.ASK_FOLLOW_UP


def test_context_builder_does_not_send_full_plan_or_transcript() -> None:
    context = build_orchestrator_context(make_answer_state())

    assert "plan" not in context
    assert "planner_input" not in context
    assert "transcript" not in context
    assert context["current_question"]["topic"] == "candidate background"


def test_interviewer_uses_structured_llm_message() -> None:
    state = make_answer_state()
    state["decision"] = OrchestratorDecision(
        action=OrchestratorAction.ASK_FOLLOW_UP,
        reason="Internal assessment reason that must remain hidden.",
        target_topic="candidate background",
        interviewer_goal="Ask for a concrete example of the candidate's contribution.",
        difficulty=Difficulty.MEDIUM,
        confidence=0.92,
    )
    expected = InterviewerOutput(
        message="Could you walk me through one concrete example and your contribution?"
    )
    client = FakeStructuredClient(result=expected)

    message = InterviewAgent(client=client, model="test-model").invoke(state)

    assert message == expected.message
    assert client.calls[0]["model"] == "test-model"
    assert client.calls[0]["response_model"] is InterviewerOutput


def test_interviewer_context_excludes_internal_assessment() -> None:
    state = make_answer_state()
    state["decision"] = OrchestratorDecision(
        action=OrchestratorAction.ASK_FOLLOW_UP,
        reason="Internal assessment reason that must remain hidden.",
        target_topic="candidate background",
        interviewer_goal="Collect a concrete example.",
        confidence=0.9,
    )

    context = build_interviewer_context(state)
    serialized = str(context)

    assert "evaluation" not in context
    assert "reason" not in context["approved_instruction"]
    assert "correctness" not in serialized
    assert "missing_concepts" not in serialized
    assert "Internal assessment reason" not in serialized


def test_interviewer_falls_back_when_provider_fails() -> None:
    state = make_answer_state()
    state["decision"] = OrchestratorDecision(
        action=OrchestratorAction.ASK_CLARIFICATION,
        reason="The answer is ambiguous.",
        confidence=0.9,
    )
    client = FakeStructuredClient(error=TimeoutError("provider timeout"))

    message = InterviewAgent(client=client).invoke(state)

    assert message == "Could you make that answer more specific and explain your reasoning?"


def make_answer_state():
    state = interview_graph.invoke(
        {
            "planner_input": PlannerInput(
                goal=InterviewGoal(
                    target_role="Backend Engineer",
                    planned_question_count=3,
                ),
                requested_competencies=["API design", "databases"],
            )
        }
    )
    state.update(
        {
            "candidate_answer": "I would use caching and measure the result.",
            "evaluation": EvaluationResult(
                correctness=3,
                depth=2,
                communication=3,
                missing_concepts=["trade-offs"],
                recommended_action=EvaluationRecommendation.FOLLOW_UP,
                follow_up_goal="Collect a concrete trade-off.",
            ),
        }
    )
    return state


def planned_question(question_id: str, competency: str, topic: str) -> PlannedQuestion:
    return PlannedQuestion(
        id=question_id,
        topic=topic,
        competency=competency,
        objective=f"Assess evidence related to {topic}.",
        difficulty=Difficulty.MEDIUM,
    )
