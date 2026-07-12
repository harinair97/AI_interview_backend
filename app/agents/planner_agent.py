import json
import logging
from collections import defaultdict

from app.agents.openai_client import StructuredOutputClient, create_openai_client
from app.agents.schemas import (
    CompetencyCoverage,
    InterviewPlan,
    InterviewSection,
    PlannedQuestion,
    PlannerInput,
    PlannerOutput,
)
from app.config import get_settings
from app.prompts import load_prompt

logger = logging.getLogger(__name__)

DEFAULT_COMPETENCIES = [
    "role fundamentals",
    "system design",
    "problem solving",
    "behavioral communication",
]


class PlannerAgent:
    """Generate a role-specific plan with a deterministic safety fallback."""

    def __init__(
        self,
        client: StructuredOutputClient | None = None,
        model: str | None = None,
    ) -> None:
        self.client = client
        self.model = model or get_settings().openai_planner_model

    def invoke(self, agent_input: PlannerInput) -> InterviewPlan:
        if self.client is not None:
            try:
                output = self.client.parse(
                    model=self.model,
                    instructions=load_prompt("planner.txt"),
                    input_text=json.dumps(agent_input.model_dump(mode="json")),
                    response_model=PlannerOutput,
                )
                plan = InterviewPlan(
                    goal=agent_input.goal,
                    competencies=output.competencies,
                    sections=output.sections,
                )
                self._validate_requested_competencies(plan, agent_input)
                return plan
            except Exception as exc:
                logger.warning(
                    "Planner model failed or returned an invalid plan; using deterministic "
                    "fallback. "
                    "error_type=%s",
                    type(exc).__name__,
                )

        return self._deterministic_plan(agent_input)

    @staticmethod
    def _validate_requested_competencies(
        plan: InterviewPlan,
        agent_input: PlannerInput,
    ) -> None:
        if not agent_input.requested_competencies:
            return
        planned = {competency.name.casefold() for competency in plan.competencies}
        missing = [
            competency
            for competency in agent_input.requested_competencies
            if competency.casefold() not in planned
        ]
        if missing:
            raise ValueError("The generated plan omitted requested competencies.")

    @staticmethod
    def _deterministic_plan(agent_input: PlannerInput) -> InterviewPlan:
        competencies = agent_input.requested_competencies or DEFAULT_COMPETENCIES
        question_count = agent_input.goal.planned_question_count
        section_questions: dict[str, list[PlannedQuestion]] = defaultdict(list)

        section_questions["introduction"].append(
            PlannedQuestion(
                id="introduction-1",
                topic="candidate background",
                competency=competencies[0],
                objective=(
                    f"Establish experience relevant to the {agent_input.goal.target_role} role."
                ),
                difficulty=agent_input.goal.difficulty,
            )
        )

        behavioral_count = 1 if question_count >= 3 else 0
        technical_count = question_count - 1 - behavioral_count
        for index in range(technical_count):
            competency = competencies[index % len(competencies)]
            section_questions["technical"].append(
                PlannedQuestion(
                    id=f"technical-{index + 1}",
                    topic=competency,
                    competency=competency,
                    objective=(
                        f"Assess practical understanding of {competency} for the "
                        f"{agent_input.goal.target_role} role."
                    ),
                    difficulty=agent_input.goal.difficulty,
                )
            )

        if behavioral_count:
            behavioral_competency = next(
                (item for item in competencies if "behavior" in item.lower()),
                competencies[-1],
            )
            section_questions["behavioral"].append(
                PlannedQuestion(
                    id="behavioral-1",
                    topic="ownership and collaboration",
                    competency=behavioral_competency,
                    objective="Collect evidence of ownership, collaboration, and communication.",
                    difficulty=agent_input.goal.difficulty,
                )
            )

        sections = [
            InterviewSection(name=name, order=order, questions=questions)
            for order, (name, questions) in enumerate(section_questions.items())
            if questions
        ]
        coverage = [
            CompetencyCoverage(name=name, importance=5 if index < 2 else 3)
            for index, name in enumerate(competencies)
        ]
        return InterviewPlan(
            goal=agent_input.goal,
            competencies=coverage,
            sections=sections,
        )


planner_agent = PlannerAgent(client=create_openai_client())
