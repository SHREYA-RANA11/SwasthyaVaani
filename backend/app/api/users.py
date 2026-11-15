from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user, require_roles
from app.models.user import User, UserRole
from app.schemas.user import ProfileUpdate, UserResponse

router = APIRouter(prefix="/users", tags=["Users"])


# Update my own profile (name, phone, DOB, gender, address, language)
@router.patch("/me", response_model=UserResponse)
def update_my_profile(
    data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    changes = data.model_dump(exclude_unset=True)

    if "phone" in changes:
        phone = (changes["phone"] or "").strip() or None
        if phone:
            taken = db.query(User).filter(
                User.phone == phone, User.id != current_user.id
            ).first()
            if taken:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Phone number is already registered",
                )
        changes["phone"] = phone

    if "full_name" in changes and changes["full_name"]:
        changes["full_name"] = changes["full_name"].strip()

    for field, value in changes.items():
        setattr(current_user, field, value)

    db.commit()
    db.refresh(current_user)
    return current_user


# Healthcare workers (and admins) can list patients
@router.get("/patients", response_model=List[UserResponse])
def list_patients(
    _: User = Depends(require_roles(UserRole.HEALTHCARE_WORKER, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    return (
        db.query(User)
        .filter(User.role == UserRole.PATIENT)
        .order_by(User.created_at.desc())
        .all()
    )
