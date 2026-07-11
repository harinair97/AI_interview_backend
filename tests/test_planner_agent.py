import pytest
from pydantic import ValidationError

from app.agents.planner_agent import planner_agent
from app.agents.schemas import Difficulty, InterviewGoal, PlannerInput


def test_planner_creates_exact_balanced_plan() -> None:
    plan = planner_agent.invoke(
        PlannerInput(
            goal=InterviewGoal(
                target_role="Data Engineer",
                difficulty=Difficulty.HARD,
                planned_question_count=6,
            ),
            requested_competencies=["SQL", "data modeling", "SQL", " communication "],
        )
    )

    questions = [question for section in plan.sections for question in section.questions]
    assert len(questions) == 6
    assert [section.name for section in plan.sections] == [
        "introduction",
        "technical",
        "behavioral",
    ]
    assert [item.name for item in plan.competencies] == ["SQL", "data modeling", "communication"]
    assert all(question.difficulty is Difficulty.HARD for question in questions)
    assert len({question.id for question in questions}) == 6


def test_one_question_plan_contains_only_introduction() -> None:
    plan = planner_agent.invoke(
        PlannerInput(
            goal=InterviewGoal(target_role="Support Engineer", planned_question_count=1)
        )
    )

    assert len(plan.sections) == 1
    assert plan.sections[0].name == "introduction"


def test_goal_rejects_invalid_question_count() -> None:
    with pytest.raises(ValidationError):
        InterviewGoal(target_role="Engineer", planned_question_count=0)
