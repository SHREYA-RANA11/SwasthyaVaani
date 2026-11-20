
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.dependencies.auth import require_roles
from app.dependencies.auth import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token
)
from app.models.user import User, UserRole
from app.schemas.user import (
    UserRegister,
    UserResponse,
    UserLogin,
    TokenResponse,
    ProfileUpdate
)

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


# User Registration
def register_user(
    user_data: UserRegister,
    role: UserRole,
    db: Session
):
    email = str(user_data.email).lower().strip()
    phone = user_data.phone.strip() if user_data.phone else None
    phone = phone or None

    existing_email = db.query(User).filter(
        User.email == email
    ).first()

    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered"
        )

    if phone:
        existing_phone = db.query(User).filter(
            User.phone == phone
        ).first()

        if existing_phone:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Phone number is already registered"
            )

    new_user = User(
    full_name=user_data.full_name.strip(),
    email=email,
    phone=phone,
    hashed_password=hash_password(user_data.password),
    role=role,
    native_language=user_data.native_language,
    preferred_language=user_data.preferred_language
)

    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to register user"
        )


# Patient Registration
@router.post(
    "/register/patient",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED
)
def register_patient(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):
    return register_user(
        user_data,
        UserRole.PATIENT,
        db
    )


# Healthcare Worker Registration
@router.post(
    "/register/healthcare-worker",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED
)
def register_healthcare_worker(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):
    return register_user(
        user_data,
        UserRole.HEALTHCARE_WORKER,
        db
    )


# User Login
@router.post(
    "/login",
    response_model=TokenResponse
)
def login(
    user_data: UserLogin,
    db: Session = Depends(get_db)
):
    email = str(user_data.email).lower().strip()

    user = db.query(User).filter(
        User.email == email
    ).first()

    if not user or not verify_password(
        user_data.password,
        user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is inactive"
        )

    access_token = create_access_token(user.id)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }

@router.get("/me", response_model=UserResponse)
def get_my_profile(
    current_user: User = Depends(get_current_user)
):
    return current_user
@router.put("/me", response_model=UserResponse)
def update_my_profile(
    profile_data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    update_data = profile_data.model_dump(exclude_unset=True)

    if "full_name" in update_data:
        update_data["full_name"] = update_data["full_name"].strip()

    if "phone" in update_data:
        phone = update_data["phone"]
        phone = phone.strip() if phone else None

        if phone:
            existing_phone = db.query(User).filter(
                User.phone == phone,
                User.id != current_user.id
            ).first()

            if existing_phone:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Phone number is already registered"
                )

        update_data["phone"] = phone

    for field, value in update_data.items():
        setattr(current_user, field, value)

    try:
        db.commit()
        db.refresh(current_user)
        return current_user

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to update profile"
        )
# Patient-only endpoint
@router.get("/patient-area")
def patient_area(
    current_user: User = Depends(
        require_roles(UserRole.PATIENT)
    )
):
    return {
        "message": "Welcome to the patient area",
        "user": current_user.full_name,
        "role": current_user.role.value
    }


# Healthcare-worker-only endpoint
@router.get("/healthcare-worker-area")
def healthcare_worker_area(
    current_user: User = Depends(
        require_roles(UserRole.HEALTHCARE_WORKER)
    )
):
    return {
        "message": "Welcome to the healthcare worker area",
        "user": current_user.full_name,
        "role": current_user.role.value
    }


# Admin-only endpoint
@router.get("/admin-area")
def admin_area(
    current_user: User = Depends(
        require_roles(UserRole.ADMIN)
    )
):
    return {
        "message": "Welcome to the admin area",
        "user": current_user.full_name,
        "role": current_user.role.value
    }
