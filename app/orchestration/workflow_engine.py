from uuid import uuid4

from langgraph.graph import END, START, StateGraph

from app.agents.planner_agent import planner_agent
from app.agents.schemas import (
    InterviewStatus,
    OrchestratorAction,
    OrchestratorDecision,
)
from app.orchestration.interview_state import InterviewState
from app.orchestration.policy_validator import validate_orchestrator_action


def create_interview_plan(state: InterviewState) -> dict:
    """Run the planner and expose its goal for the remaining workflow."""

    plan = planner_agent.invoke(state["planner_input"])
    return {"plan": plan, "goal": plan.goal}


def initialize_interview(state: InterviewState) -> dict:
    """Create server-owned state; later this node will persist the planner output."""

    plan = state["plan"]
    current_section = plan.sections[0]
    remaining_sections = [section.name for section in plan.sections[1:]]
    available_topics = [
        question.topic for section in plan.sections for question in section.questions
    ]
    return {
        "interview_id": state.get("interview_id", str(uuid4())),
        "status": InterviewStatus.IN_PROGRESS,
        "current_section": current_section.name,
        "question_index": 0,
        "questions_answered": 0,
        "follow_up_count": 0,
        "max_follow_ups": 2,
        "clarification_count": 0,
        "max_clarifications": 1,
        "minimum_questions": min(3, state["goal"].planned_question_count),
        "remaining_questions_in_section": max(0, len(current_section.questions) - 1),
        "remaining_sections": remaining_sections,
        "available_topics": available_topics,
        "coverage": plan.competencies,
        "current_difficulty": state["goal"].difficulty,
        "difficulty_signal_streak": 0,
        "minimum_orchestrator_confidence": 0.6,
        "events": ["INTERVIEW_INITIALIZED"],
    }


def choose_opening_action(state: InterviewState) -> dict:
    """Credential-free placeholder for the future orchestrator agent node."""

    opening_question = state["plan"].sections[0].questions[0]
    return {
        "decision": OrchestratorDecision(
            action=OrchestratorAction.ASK_INITIAL_QUESTION,
            reason="A new interview requires an opening question.",
            target_topic=opening_question.topic,
            interviewer_goal=opening_question.objective,
            difficulty=opening_question.difficulty,
            confidence=1.0,
        )
    }


def render_opening_message(state: InterviewState) -> dict:
    """Credential-free placeholder for the future interview agent node."""

    role = state["goal"].target_role
    return {
        "interviewer_message": (
            f"Welcome. To get started, could you briefly describe the experience "
            f"that best prepares you for a {role} role?"
        ),
        "events": [*state["events"], "OPENING_QUESTION_CREATED"],
    }


def validate_opening_action(state: InterviewState) -> dict:
    """Apply the same policy boundary that future model decisions must cross."""

    return {"decision": validate_orchestrator_action(state["decision"], state)}


def build_interview_graph():
    builder = StateGraph(InterviewState)
    builder.add_node("create_interview_plan", create_interview_plan)
    builder.add_node("initialize_interview", initialize_interview)
    builder.add_node("choose_opening_action", choose_opening_action)
    builder.add_node("validate_opening_action", validate_opening_action)
    builder.add_node("render_opening_message", render_opening_message)
    builder.add_edge(START, "create_interview_plan")
    builder.add_edge("create_interview_plan", "initialize_interview")
    builder.add_edge("initialize_interview", "choose_opening_action")
    builder.add_edge("choose_opening_action", "validate_opening_action")
    builder.add_edge("validate_opening_action", "render_opening_message")
    builder.add_edge("render_opening_message", END)
    return builder.compile()


interview_graph = build_interview_graph()
