from collections import defaultdict

from app.agents.schemas import (
    CompetencyCoverage,
    InterviewPlan,
    InterviewSection,
    PlannedQuestion,
    PlannerInput,
)

DEFAULT_COMPETENCIES = [
    "role fundamentals",
    "system design",
    "problem solving",
    "behavioral communication",
]


class PlannerAgent:
    """Build a valid MVP plan without depending on an LLM provider."""

    def invoke(self, agent_input: PlannerInput) -> InterviewPlan:
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
                    objective="Collect evidence of ownership, collaboration, and clear communication.",
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


planner_agent = PlannerAgent()
