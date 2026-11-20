import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.database import get_db
from app.dependencies.auth import get_current_user, require_roles
from app.models.prescription import Medication, Prescription
from app.models.user import User, UserRole
from app.schemas.prescription import (
    AnalyzeRequest, MedicationOut, PrescriptionDetail, PrescriptionListItem,
)
from app.services import ai

router = APIRouter(prefix="/prescriptions", tags=["Prescriptions"])

IST = timezone(timedelta(hours=5, minutes=30))
LANGS = {"English", "Hindi", "Gujarati"}


def _today() -> date:
    return datetime.now(IST).date()


def _sniff(data: bytes) -> Optional[str]:
    """Identify the real file type from its first bytes (never trust the filename)."""
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def _upload_dir() -> Path:
    d = Path(settings.UPLOAD_DIR)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _item(rx: Prescription) -> PrescriptionListItem:
    return PrescriptionListItem(
        id=rx.id, patient_id=rx.patient_id,
        patient_name=rx.patient.full_name if rx.patient else None,
        title=rx.title, language=rx.language, status=rx.status,
        doctor_name=rx.doctor_name, diagnosis=rx.diagnosis,
        needs_review=rx.needs_review, reviewed_at=rx.reviewed_at,
        ai_provider=rx.ai_provider, medicine_count=len(rx.medications),
        created_at=rx.created_at,
    )


def _detail(rx: Prescription) -> PrescriptionDetail:
    return PrescriptionDetail(
        **_item(rx).model_dump(),
        summary=rx.summary, extracted_text=rx.extracted_text,
        warnings=rx.warnings or [], follow_up=rx.follow_up,
        confidence=rx.confidence, error_message=rx.error_message,
        reviewed_by_name=rx.reviewed_by.full_name if rx.reviewed_by else None,
        medications=[MedicationOut.model_validate(m) for m in rx.medications],
    )


def _load(db: Session, rx_id: int, user: User) -> Prescription:
    """Fetch a prescription the user is allowed to see, or 404."""
    rx = (
        db.query(Prescription)
        .options(joinedload(Prescription.medications), joinedload(Prescription.patient),
                 joinedload(Prescription.reviewed_by))
        .filter(Prescription.id == rx_id)
        .first()
    )
    if not rx or (user.role == UserRole.PATIENT and rx.patient_id != user.id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Prescription not found")
    return rx

def _run_analysis(db: Session, rx: Prescription, image: bytes, language: str) -> None:
    """Call the AI and store the result. Never raises: failures are saved on the record."""
    rx.language = language
    rx.status = "processing"
    rx.error_message = None
    db.commit()

    # Assess image quality before AI analysis.
    image_quality_warnings = []

    try:
        quality = ai.assess_image_quality(image)

        # Only use warnings that have been tested and calibrated provisionally.
        supported_warnings = {"low_resolution", "possible_blur"}

        image_quality_warnings = [
            warning
            for warning in quality["warnings"]
            if warning in supported_warnings
        ]

    except ai.AIError:
        image_quality_warnings = ["image_quality_assessment_failed"]

    try:
        result = ai.analyze_prescription(image, rx.content_type, language)

    except ai.AIError as e:
        rx.status = "failed"
        rx.error_message = str(e)[:500]
        rx.warnings = image_quality_warnings
        db.commit()
        return

    except Exception:
        rx.status = "failed"
        rx.error_message = "Something went wrong while reading the prescription."
        rx.warnings = image_quality_warnings
        db.commit()
        return

    rx.doctor_name = (result.doctor_name or None) and result.doctor_name[:200]
    rx.diagnosis = (result.diagnosis or None) and result.diagnosis[:500]
    rx.extracted_text = result.extracted_text
    rx.summary = result.summary

    # Preserve AI warnings and add image-quality warnings without duplicates.
    rx.warnings = list(dict.fromkeys(
        (result.warnings or []) + image_quality_warnings
    ))

    rx.follow_up = (result.follow_up or None) and result.follow_up[:500]
    rx.confidence = result.confidence

    # Poor image quality requires additional review.
    rx.needs_review = (
        result.needs_review or bool(image_quality_warnings)
    )

    rx.reviewed_by_id, rx.reviewed_at = None, None
    rx.ai_provider = settings.AI_PROVIDER.lower()
    rx.status = "processed"

    # Replace medicines (old dose history goes with them) and build the schedule from today.
    rx.medications.clear()
    start = _today()

    for m in result.medicines:
        rx.medications.append(Medication(
            name=m.name,
            dose=m.dose and m.dose[:100],
            frequency_per_day=m.frequency_per_day,
            times=m.times,
            duration_days=m.duration_days,
            start_date=start,
            end_date=start + timedelta(days=m.duration_days - 1) if m.duration_days else None,
            food=m.food,
            instructions_simple=m.instructions_simple,
            instructions_original=m.instructions_original,
        ))

    db.commit()


@router.post("", response_model=PrescriptionDetail, status_code=status.HTTP_201_CREATED)
def upload_prescription(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    language: Optional[str] = Form(None),
    user: User = Depends(require_roles(UserRole.PATIENT)),
    db: Session = Depends(get_db),
):
    limit = settings.MAX_UPLOAD_MB * 1024 * 1024
    data = file.file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            f"File is too large (maximum {settings.MAX_UPLOAD_MB} MB)")
    mime = _sniff(data)
    if not mime:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                            "Please upload a JPG, PNG or WEBP photo of the prescription")

    lang = language if language in LANGS else (user.preferred_language if user.preferred_language in LANGS else "English")
    stored = f"{uuid.uuid4().hex}.{mime.split('/')[1].replace('jpeg', 'jpg')}"
    (_upload_dir() / stored).write_bytes(data)

    rx = Prescription(
        patient_id=user.id,
        title=(title or "").strip()[:200] or f"Prescription {_today().strftime('%d %b %Y')}",
        original_filename=(file.filename or "")[:255] or None,
        stored_filename=stored, content_type=mime, language=lang,
    )
    db.add(rx)
    db.commit()
    db.refresh(rx)

    _run_analysis(db, rx, data, lang)
    return _detail(_load(db, rx.id, user))


@router.get("", response_model=List[PrescriptionListItem])
def list_prescriptions(
    patient_id: Optional[int] = None,
    needs_review: Optional[bool] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Prescription).options(joinedload(Prescription.medications), joinedload(Prescription.patient))
    if user.role == UserRole.PATIENT:
        q = q.filter(Prescription.patient_id == user.id)
    elif patient_id:
        q = q.filter(Prescription.patient_id == patient_id)
    if needs_review is not None:
        q = q.filter(Prescription.needs_review.is_(needs_review), Prescription.status == "processed")
    return [_item(r) for r in q.order_by(Prescription.created_at.desc()).all()]


@router.get("/{rx_id}", response_model=PrescriptionDetail)
def get_prescription(rx_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _detail(_load(db, rx_id, user))


@router.get("/{rx_id}/file")
def get_prescription_file(rx_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rx = _load(db, rx_id, user)
    path = _upload_dir() / rx.stored_filename
    if not path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File not found")
    return FileResponse(path, media_type=rx.content_type)


@router.post("/{rx_id}/analyze", response_model=PrescriptionDetail)
def reanalyze(
    rx_id: int, body: AnalyzeRequest,
    user: User = Depends(require_roles(UserRole.PATIENT)),
    db: Session = Depends(get_db),
):
    """Retry a failed reading, or translate the same prescription into another language."""
    rx = _load(db, rx_id, user)
    path = _upload_dir() / rx.stored_filename
    if not path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File not found")
    _run_analysis(db, rx, path.read_bytes(), body.language)
    return _detail(_load(db, rx_id, user))


@router.post("/{rx_id}/review", response_model=PrescriptionDetail)
def mark_reviewed(
    rx_id: int,
    user: User = Depends(require_roles(UserRole.HEALTHCARE_WORKER, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """A healthcare worker confirms the AI explanation matches the original prescription."""
    rx = _load(db, rx_id, user)
    if rx.status != "processed":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only a processed prescription can be verified")
    rx.needs_review = False
    rx.reviewed_by_id = user.id
    rx.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    return _detail(_load(db, rx_id, user))


@router.delete("/{rx_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_prescription(
    rx_id: int,
    user: User = Depends(require_roles(UserRole.PATIENT)),
    db: Session = Depends(get_db),
):
    rx = _load(db, rx_id, user)
    path = _upload_dir() / rx.stored_filename
    db.delete(rx)
    db.commit()
    path.unlink(missing_ok=True)
