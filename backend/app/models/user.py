
import enum

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    Date,
    DateTime,
    Enum,
    func
)

from app.core.database import Base


class UserRole(str, enum.Enum):
    PATIENT = "patient"
    HEALTHCARE_WORKER = "healthcare_worker"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    # Account information
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone = Column(String(20), unique=True, nullable=True)
    hashed_password = Column(String(255), nullable=False)

    # Role and account status
    role = Column(
        Enum(UserRole, name="user_role"),
        default=UserRole.PATIENT,
        nullable=False
    )
    is_active = Column(Boolean, default=True, nullable=False)

    # Patient profile information
    date_of_birth = Column(Date, nullable=True)
    gender = Column(String(20), nullable=True)
    address = Column(String(500), nullable=True)
    preferred_language = Column(
        String(50),
        default="English",
        nullable=False
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
