from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_create_interview_uses_request_goal_and_competencies() -> None:
    response = client.post(
        "/api/v1/interviews",
        json={
            "target_role": "Data Engineer",
            "difficulty": "HARD",
            "planned_question_count": 5,
            "competencies": ["SQL", "data modeling"],
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["plan"]["goal"]["target_role"] == "Data Engineer"
    assert body["plan"]["goal"]["planned_question_count"] == 5
    assert [item["name"] for item in body["plan"]["competencies"]] == [
        "SQL",
        "data modeling",
    ]
    assert "Data Engineer" in body["interviewer_message"]

    persisted = client.get(f"/api/v1/interviews/{body['interview_id']}")
    assert persisted.status_code == 200
    snapshot = persisted.json()
    assert snapshot["target_role"] == "Data Engineer"
    assert snapshot["runtime_state"]["decision"]["action"] == "ASK_INITIAL_QUESTION"
    assert [event["event_type"] for event in snapshot["events"]] == [
        "INTERVIEW_INITIALIZED",
        "OPENING_QUESTION_CREATED",
    ]


def test_create_interview_rejects_invalid_question_count() -> None:
    response = client.post(
        "/api/v1/interviews",
        json={"target_role": "Engineer", "planned_question_count": 0},
    )

    assert response.status_code == 422


def test_get_missing_interview_returns_404() -> None:
    response = client.get("/api/v1/interviews/does-not-exist")

    assert response.status_code == 404
