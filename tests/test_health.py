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


def test_create_interview_rejects_invalid_question_count() -> None:
    response = client.post(
        "/api/v1/interviews",
        json={"target_role": "Engineer", "planned_question_count": 0},
    )

    assert response.status_code == 422
