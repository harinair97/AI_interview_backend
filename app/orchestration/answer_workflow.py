from langgraph.graph import END, START, StateGraph

from app.agents.evaluation_agent import evaluation_agent
from app.agents.interview_agent import interview_agent
from app.agents.orchestrator_agent import orchestrator_agent
from app.agents.schemas import (
    EvaluationInput,
    InterviewStatus,
    OrchestratorAction,
    OrchestratorDecision,
)
from app.orchestration.interview_state import InterviewState
from app.orchestration.policy_validator import validate_orchestrator_action


def record_candidate_answer(state: InterviewState) -> dict:
    is_first_answer = (
        state.get("follow_up_count", 0) == 0 and state.get("clarification_count", 0) == 0
    )
    return {
        "questions_answered": state.get("questions_answered", 0) + int(is_first_answer)
    }


def evaluate_answer(state: InterviewState) -> dict:
    question = _all_questions(state)[state["question_index"]]
    evaluation = evaluation_agent.invoke(
        EvaluationInput(question=question, candidate_answer=state["candidate_answer"])
    )
    return {"evaluation": evaluation}


def recommend_next_action(state: InterviewState) -> dict:
    return {"decision": orchestrator_agent.invoke(state)}


def validate_next_action(state: InterviewState) -> dict:
    return {"decision": validate_orchestrator_action(state["decision"], state)}


def record_decision_history(state: InterviewState) -> dict:
    history = state.get("recent_decisions", [])
    return {"recent_decisions": [*history[-4:], state["decision"].action.value]}


def apply_state_transition(state: InterviewState) -> dict:
    action = state["decision"].action

    if action is OrchestratorAction.ASK_FOLLOW_UP:
        return {"follow_up_count": state.get("follow_up_count", 0) + 1}

    if action is OrchestratorAction.ASK_CLARIFICATION:
        return {"clarification_count": state.get("clarification_count", 0) + 1}

    if action is OrchestratorAction.CHALLENGE_ANSWER:
        return {"follow_up_count": state.get("follow_up_count", 0) + 1}

    if action is OrchestratorAction.ADJUST_DIFFICULTY:
        return {"current_difficulty": state["decision"].difficulty}

    if action is OrchestratorAction.END_INTERVIEW:
        return {"status": InterviewStatus.COMPLETED}

    if action in {
        OrchestratorAction.MOVE_TO_NEXT_QUESTION,
        OrchestratorAction.MOVE_TO_NEXT_SECTION,
    }:
        next_index = state["question_index"] + 1
        questions = _all_questions(state)
        if next_index >= len(questions):
            return {
                "status": InterviewStatus.COMPLETED,
                "decision": OrchestratorDecision(
                    action=OrchestratorAction.END_INTERVIEW,
                    reason="All planned questions have been completed.",
                    confidence=1.0,
                ),
            }

        section_index, position_in_section = _question_location(state, next_index)
        section = state["plan"].sections[section_index]
        return {
            "question_index": next_index,
            "current_section": section.name,
            "remaining_questions_in_section": len(section.questions) - position_in_section - 1,
            "remaining_sections": [
                item.name for item in state["plan"].sections[section_index + 1 :]
            ],
            "follow_up_count": 0,
            "clarification_count": 0,
            "current_difficulty": questions[next_index].difficulty,
        }

    return {}


def render_interviewer_message(state: InterviewState) -> dict:
    return {"interviewer_message": interview_agent.invoke(state)}


def _all_questions(state: InterviewState):
    return [question for section in state["plan"].sections for question in section.questions]


def _question_location(state: InterviewState, global_index: int) -> tuple[int, int]:
    seen = 0
    for section_index, section in enumerate(state["plan"].sections):
        if global_index < seen + len(section.questions):
            return section_index, global_index - seen
        seen += len(section.questions)
    raise IndexError("Question index is outside the interview plan.")


def build_answer_graph():
    builder = StateGraph(InterviewState)
    builder.add_node("record_candidate_answer", record_candidate_answer)
    builder.add_node("evaluate_answer", evaluate_answer)
    builder.add_node("recommend_next_action", recommend_next_action)
    builder.add_node("validate_next_action", validate_next_action)
    builder.add_node("record_decision_history", record_decision_history)
    builder.add_node("apply_state_transition", apply_state_transition)
    builder.add_node("render_interviewer_message", render_interviewer_message)
    builder.add_edge(START, "record_candidate_answer")
    builder.add_edge("record_candidate_answer", "evaluate_answer")
    builder.add_edge("evaluate_answer", "recommend_next_action")
    builder.add_edge("recommend_next_action", "validate_next_action")
    builder.add_edge("validate_next_action", "record_decision_history")
    builder.add_edge("record_decision_history", "apply_state_transition")
    builder.add_edge("apply_state_transition", "render_interviewer_message")
    builder.add_edge("render_interviewer_message", END)
    return builder.compile()


answer_graph = build_answer_graph()
