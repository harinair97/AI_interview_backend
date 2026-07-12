from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.interview import InterviewEvent, InterviewRecord


class InterviewRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, interview: InterviewRecord) -> InterviewRecord:
        self.session.add(interview)
        self.session.flush()
        return interview

    def add_events(self, interview_id: str, events: list[tuple[str, dict]]) -> None:
        current_sequence = self.session.scalar(
            select(func.coalesce(func.max(InterviewEvent.sequence), 0)).where(
                InterviewEvent.interview_id == interview_id
            )
        )
        self.session.add_all(
            InterviewEvent(
                interview_id=interview_id,
                sequence=current_sequence + offset,
                event_type=event_type,
                payload=payload,
            )
            for offset, (event_type, payload) in enumerate(events, start=1)
        )

    def get(self, interview_id: str) -> InterviewRecord | None:
        statement = (
            select(InterviewRecord)
            .where(InterviewRecord.id == interview_id)
            .options(selectinload(InterviewRecord.events))
        )
        return self.session.scalar(statement)
