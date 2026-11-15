from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class MedicationOut(BaseModel):
    id: int
    name: str
    dose: Optional[str]
    frequency_per_day: int
    times: List[str]
    duration_days: Optional[int]
    start_date: date
    end_date: Optional[date]
    food: str
    instructions_simple: Optional[str]
    instructions_original: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class PrescriptionListItem(BaseModel):
    id: int
    patient_id: int
    patient_name: Optional[str] = None
    title: str
    language: str
    status: str
    doctor_name: Optional[str]
    diagnosis: Optional[str]
    needs_review: bool
    reviewed_at: Optional[datetime]
    ai_provider: Optional[str]
    medicine_count: int = 0
    created_at: datetime


class PrescriptionDetail(PrescriptionListItem):
    summary: Optional[str]
    extracted_text: Optional[str]
    warnings: List[str]
    follow_up: Optional[str]
    confidence: Optional[str]
    error_message: Optional[str]
    reviewed_by_name: Optional[str] = None
    medications: List[MedicationOut]
    disclaimer: str = (
        "This is an automatic explanation to help you understand your prescription. "
        "It is not medical advice. Always follow your doctor's instructions and ask your doctor "
        "or pharmacist if you are unsure."
    )


class AnalyzeRequest(BaseModel):
    language: str = Field(pattern="^(English|Hindi|Gujarati)$")


class DoseOut(BaseModel):
    medication_id: int
    prescription_id: int
    medication_name: str
    dose: Optional[str]
    food: str
    instructions: Optional[str]
    scheduled_date: date
    scheduled_time: str
    status: str  # taken | due | missed | upcoming
    
    
class AsNeededOut(BaseModel):
    medication_id: int
    prescription_id: int
    medication_name: str
    dose: Optional[str]
    instructions: Optional[str]


class DosesResponse(BaseModel):
    date: date
    doses: List[DoseOut]
    as_needed: List[AsNeededOut]
    taken: int
    total: int
    missed: int


class DoseMark(BaseModel):
    medication_id: int
    date: date
    time: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    taken: bool = True
