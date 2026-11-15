from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import require_roles
from app.models.prescription import Prescription
from app.models.user import User, UserRole
from app.schemas.user import ActiveUpdate, UserResponse

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/stats")
def get_stats(
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    total = db.query(func.count(User.id)).scalar() or 0
    active = db.query(func.count(User.id)).filter(User.is_active.is_(True)).scalar() or 0
    by_role = {r.value: 0 for r in UserRole}
    for role, count in db.query(User.role, func.count(User.id)).group_by(User.role).all():
        by_role[role.value] = count
    by_language = {
        lang: count
        for lang, count in db.query(User.preferred_language, func.count(User.id))
        .group_by(User.preferred_language)
        .all()
    }
    total_rx = db.query(func.count(Prescription.id)).scalar() or 0
    pending_rx = (
        db.query(func.count(Prescription.id))
        .filter(Prescription.needs_review.is_(True), Prescription.status == "processed")
        .scalar() or 0
    )
    return {
        "total_prescriptions": total_rx,
        "prescriptions_needing_review": pending_rx,
        "total_users": total,
        "active_users": active,
        "inactive_users": total - active,
        "by_role": by_role,
        "by_language": by_language,
    }


@router.get("/users", response_model=List[UserResponse])
def list_users(
    role: Optional[UserRole] = None,
    _: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    return query.order_by(User.created_at.desc()).all()


@router.patch("/users/{user_id}/active", response_model=UserResponse)
def set_user_active(
    user_id: int,
    data: ActiveUpdate,
    admin: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account",
        )
    user.is_active = data.is_active
    db.commit()
    db.refresh(user)
    return user
