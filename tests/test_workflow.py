from app.agents.schemas import Difficulty, InterviewGoal, OrchestratorAction
from app.orchestration.workflow_engine import interview_graph


def test_demo_graph_creates_opening_question() -> None:
    result = interview_graph.invoke(
        {
            "goal": InterviewGoal(
                target_role="Backend Software Engineer",
                difficulty=Difficulty.MEDIUM,
                planned_question_count=8,
            )
        }
    )

    assert result["status"] == "IN_PROGRESS"
    assert result["decision"].action is OrchestratorAction.ASK_INITIAL_QUESTION
    assert "Backend Software Engineer" in result["interviewer_message"]
    assert result["events"] == ["INTERVIEW_INITIALIZED", "OPENING_QUESTION_CREATED"]
