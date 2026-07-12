from fastapi.encoders import jsonable_encoder

from app.orchestration.interview_state import InterviewState


def build_orchestrator_context(state: InterviewState) -> dict:
    """Build the compact decision context instead of sending the full snapshot."""

    questions = [
        question for section in state["plan"].sections for question in section.questions
    ]
    current_question = questions[state["question_index"]]
    return jsonable_encoder(
        {
            "interview_goal": state["goal"],
            "current_state": {
                "section": state["current_section"],
                "question_index": state["question_index"],
                "follow_up_count": state.get("follow_up_count", 0),
                "max_follow_ups": state.get("max_follow_ups", 2),
                "clarification_count": state.get("clarification_count", 0),
                "max_clarifications": state.get("max_clarifications", 1),
                "questions_answered": state.get("questions_answered", 0),
                "remaining_questions": len(questions) - state["question_index"] - 1,
                "remaining_sections": state.get("remaining_sections", []),
            },
            "current_question": current_question,
            "candidate_answer": state["candidate_answer"],
            "evaluation": state["evaluation"],
            "coverage": state.get("coverage", []),
            "available_topics": state.get("available_topics", []),
            "recent_decisions": state.get("recent_decisions", [])[-5:],
        }
    )


def build_interviewer_context(state: InterviewState) -> dict:
    """Expose only candidate-safe information needed to phrase the next message."""

    questions = [
        question for section in state["plan"].sections for question in section.questions
    ]
    current_question = questions[state["question_index"]]
    decision = state["decision"]
    return jsonable_encoder(
        {
            "target_role": state["goal"].target_role,
            "section": state["current_section"],
            "approved_instruction": {
                "action": decision.action,
                "target_topic": decision.target_topic,
                "interviewer_goal": decision.interviewer_goal,
                "difficulty": decision.difficulty,
                "next_section": decision.next_section,
            },
            "current_question": current_question,
            "candidate_answer": state.get("candidate_answer"),
        }
    )
