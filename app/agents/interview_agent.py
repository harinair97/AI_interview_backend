from app.agents.schemas import OrchestratorAction
from app.orchestration.interview_state import InterviewState


class InterviewAgent:
    """Render approved instructions into safe candidate-facing language."""

    def invoke(self, state: InterviewState) -> str:
        decision = state["decision"]

        if decision.action is OrchestratorAction.ASK_CLARIFICATION:
            return "Could you make that answer more specific and explain your reasoning?"

        if decision.action is OrchestratorAction.ASK_FOLLOW_UP:
            return (
                f"Could you give a concrete example involving {decision.target_topic} "
                "and explain the trade-offs you considered?"
            )

        if decision.action is OrchestratorAction.CHALLENGE_ANSWER:
            return (
                f"Let's examine {decision.target_topic} more closely. What limitations "
                "or failure cases might challenge your approach?"
            )

        if decision.action is OrchestratorAction.END_INTERVIEW:
            return "Thank you. That completes the planned interview."

        question = _current_question(state)
        return (
            f"Let's move to {question.topic}. {question.objective} "
            "How would you approach this in practice?"
        )


def _current_question(state: InterviewState):
    questions = [
        question for section in state["plan"].sections for question in section.questions
    ]
    return questions[state["question_index"]]


interview_agent = InterviewAgent()
