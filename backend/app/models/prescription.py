from sqlalchemy import (
    JSON, Boolean, Column, Date, DateTime, ForeignKey, Integer,
    String, Text, UniqueConstraint, func,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class Prescription(Base):
    __tablename__ = "prescriptions"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    title = Column(String(200), nullable=False)
    original_filename = Column(String(255), nullable=True)
    stored_filename = Column(String(255), nullable=False)
    content_type = Column(String(50), nullable=False)

    language = Column(String(50), nullable=False, default="English")
    status = Column(String(20), nullable=False, default="processing")  # processing | processed | failed
    error_message = Column(String(500), nullable=True)

    # AI output
    doctor_name = Column(String(200), nullable=True)
    diagnosis = Column(String(500), nullable=True)
    extracted_text = Column(Text, nullable=True)       # what is printed on the paper
    summary = Column(Text, nullable=True)              # simple explanation in `language`
    warnings = Column(JSON, nullable=False, default=list)
    follow_up = Column(String(500), nullable=True)
    confidence = Column(String(20), nullable=True)
    ai_provider = Column(String(30), nullable=True)

    # Human safety check
    needs_review = Column(Boolean, nullable=False, default=False)
    reviewed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    patient = relationship("User", foreign_keys=[patient_id])
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])
    medications = relationship(
        "Medication", back_populates="prescription",
        cascade="all, delete-orphan", order_by="Medication.id",
    )


class Medication(Base):
    __tablename__ = "medications"

    id = Column(Integer, primary_key=True, index=True)
    prescription_id = Column(Integer, ForeignKey("prescriptions.id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String(200), nullable=False)
    dose = Column(String(100), nullable=True)
    frequency_per_day = Column(Integer, nullable=False, default=1)   # 0 = only when needed
    times = Column(JSON, nullable=False, default=list)               # ["08:00", "20:00"]
    duration_days = Column(Integer, nullable=True)                   # None = ongoing
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    food = Column(String(20), nullable=False, default="any")        # before_food | after_food | with_food | any
    instructions_simple = Column(Text, nullable=True)
    instructions_original = Column(Text, nullable=True)

    prescription = relationship("Prescription", back_populates="medications")
    dose_logs = relationship("DoseLog", back_populates="medication", cascade="all, delete-orphan")


class DoseLog(Base):
    """One row = the patient confirmed taking a scheduled dose."""
    __tablename__ = "dose_logs"
    __table_args__ = (
        UniqueConstraint("medication_id", "scheduled_date", "scheduled_time", name="uq_dose_slot"),
    )

    id = Column(Integer, primary_key=True)
    medication_id = Column(Integer, ForeignKey("medications.id", ondelete="CASCADE"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    scheduled_date = Column(Date, nullable=False)
    scheduled_time = Column(String(5), nullable=False)
    taken_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    medication = relationship("Medication", back_populates="dose_logs")
