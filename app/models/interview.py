from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class InterviewRecord(Base):
    __tablename__ = "interviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    target_role: Mapped[str] = mapped_column(String(255), nullable=False)
    goal: Mapped[dict] = mapped_column(JSON, nullable=False)
    plan: Mapped[dict] = mapped_column(JSON, nullable=False)
    runtime_state: Mapped[dict] = mapped_column(JSON, nullable=False)
    interviewer_message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    events: Mapped[list["InterviewEvent"]] = relationship(
        back_populates="interview",
        cascade="all, delete-orphan",
        order_by="InterviewEvent.sequence",
    )


class InterviewEvent(Base):
    __tablename__ = "interview_events"
    __table_args__ = (
        UniqueConstraint("interview_id", "sequence", name="uq_interview_event_sequence"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    interview_id: Mapped[str] = mapped_column(
        ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    interview: Mapped[InterviewRecord] = relationship(back_populates="events")
