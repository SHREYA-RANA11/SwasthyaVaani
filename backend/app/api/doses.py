from datetime import date, datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import require_roles
from app.models.prescription import DoseLog, Medication, Prescription
from app.models.user import User, UserRole
from app.schemas.prescription import AsNeededOut, DoseMark, DoseOut, DosesResponse

router = APIRouter(prefix="/doses", tags=["Medication schedule"])

IST = timezone(timedelta(hours=5, minutes=30))
GRACE_MINUTES = 60  # a dose is "due" for an hour after its time, then "missed"


def _minutes(hhmm: str) -> int:
    return int(hhmm[:2]) * 60 + int(hhmm[3:])


@router.get("", response_model=DosesResponse)
def todays_doses(
    day: Optional[date] = Query(None, alias="date", description="Patient's local date, YYYY-MM-DD"),
    now: Optional[str] = Query(None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$",
                               description="Patient's local time, HH:MM"),
    user: User = Depends(require_roles(UserRole.PATIENT)),
    db: Session = Depends(get_db),
):
    """The patient's schedule for one day, with each dose marked taken / due / missed / upcoming."""
    clock = datetime.now(IST)
    day = day or clock.date()
    now_min = _minutes(now) if now else clock.hour * 60 + clock.minute
    # If the app sends its local time, that day is "today"; otherwise use India time
    ref_day = day if now else clock.date()

    meds = (
        db.query(Medication).join(Prescription)
        .filter(
            Prescription.patient_id == user.id,
            Prescription.status == "processed",
            Medication.start_date <= day,
            (Medication.end_date.is_(None)) | (Medication.end_date >= day),
        ).order_by(Medication.id).all()
    )
    logged = {
        (d.medication_id, d.scheduled_time)
        for d in db.query(DoseLog).filter(
            DoseLog.patient_id == user.id, DoseLog.scheduled_date == day
        ).all()
    }

    doses, as_needed = [], []
    for m in meds:
        if m.frequency_per_day == 0 or not m.times:
            as_needed.append(AsNeededOut(
                medication_id=m.id, prescription_id=m.prescription_id,
                medication_name=m.name, dose=m.dose, instructions=m.instructions_simple))
            continue
        for t in m.times:
            if (m.id, t) in logged:
                st = "taken"
            else:
                diff = now_min - _minutes(t)
                if day < ref_day:
                    st = "missed"
                elif day > ref_day or diff < 0:
                    st = "upcoming"
                elif diff <= GRACE_MINUTES:
                    st = "due"
                else:
                    st = "missed"
            doses.append(DoseOut(
                medication_id=m.id, prescription_id=m.prescription_id, medication_name=m.name,
                dose=m.dose, food=m.food, instructions=m.instructions_simple,
                scheduled_date=day, scheduled_time=t, status=st))
    doses.sort(key=lambda d: (d.scheduled_time, d.medication_name))
    return DosesResponse(
        date=day, doses=doses, as_needed=as_needed,
        taken=sum(d.status == "taken" for d in doses), total=len(doses),
        missed=sum(d.status == "missed" for d in doses),
    )


@router.post("/mark", status_code=status.HTTP_204_NO_CONTENT)
def mark_dose(
    body: DoseMark,
    user: User = Depends(require_roles(UserRole.PATIENT)),
    db: Session = Depends(get_db),
):
    med = (
        db.query(Medication).join(Prescription)
        .filter(Medication.id == body.medication_id, Prescription.patient_id == user.id).first()
    )
    if not med or body.time not in (med.times or []):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "That dose is not part of your schedule")

    existing = db.query(DoseLog).filter(
        DoseLog.medication_id == med.id, DoseLog.scheduled_date == body.date,
        DoseLog.scheduled_time == body.time).first()
    if body.taken and not existing:
        db.add(DoseLog(medication_id=med.id, patient_id=user.id,
                       scheduled_date=body.date, scheduled_time=body.time))
    elif not body.taken and existing:
        db.delete(existing)
    db.commit()
