from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

DETAILED_ANSWER = " ".join(
    [
        "I would begin by clarifying the requirements and measuring the current behavior.",
        "Then I would compare several approaches, document their operational trade-offs,",
        "test the riskiest assumptions, and deploy incrementally with monitoring and a",
        "rollback plan. I would also communicate the decision and evidence to the team.",
    ]
)


def create_three_question_interview() -> str:
    response = client.post(
        "/api/v1/interviews",
        json={
            "target_role": "Backend Engineer",
            "planned_question_count": 3,
            "competencies": ["API design", "databases"],
        },
    )
    assert response.status_code == 201
    return response.json()["interview_id"]


def test_answer_turn_progresses_and_persists_events() -> None:
    interview_id = create_three_question_interview()

    clarification = client.post(
        f"/api/v1/interviews/{interview_id}/answers",
        json={"answer": "I built APIs."},
    )
    assert clarification.status_code == 200
    assert clarification.json()["decision"]["action"] == "ASK_CLARIFICATION"

    forced_move = client.post(
        f"/api/v1/interviews/{interview_id}/answers",
        json={"answer": "Using Python."},
    )
    assert forced_move.status_code == 200
    assert forced_move.json()["decision"]["action"] == "MOVE_TO_NEXT_QUESTION"

    second_question = client.post(
        f"/api/v1/interviews/{interview_id}/answers",
        json={"answer": DETAILED_ANSWER},
    )
    assert second_question.status_code == 200
    assert second_question.json()["decision"]["action"] == "MOVE_TO_NEXT_QUESTION"

    completed = client.post(
        f"/api/v1/interviews/{interview_id}/answers",
        json={"answer": DETAILED_ANSWER},
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "COMPLETED"
    assert completed.json()["decision"]["action"] == "END_INTERVIEW"

    snapshot = client.get(f"/api/v1/interviews/{interview_id}").json()
    assert snapshot["runtime_state"]["questions_answered"] == 3
    assert snapshot["runtime_state"]["question_index"] == 2
    assert len(snapshot["events"]) == 18
    assert snapshot["events"][2]["event_type"] == "CANDIDATE_ANSWER_SUBMITTED"
    assert snapshot["events"][2]["payload"]["answer"] == "I built APIs."
    assert snapshot["events"][-1]["event_type"] == "INTERVIEWER_MESSAGE_CREATED"

    rejected = client.post(
        f"/api/v1/interviews/{interview_id}/answers",
        json={"answer": "One more answer."},
    )
    assert rejected.status_code == 409


def test_answer_requires_existing_interview_and_nonempty_text() -> None:
    missing = client.post(
        "/api/v1/interviews/missing/answers",
        json={"answer": "An answer."},
    )
    assert missing.status_code == 404

    interview_id = create_three_question_interview()
    invalid = client.post(
        f"/api/v1/interviews/{interview_id}/answers",
        json={"answer": ""},
    )
    assert invalid.status_code == 422
