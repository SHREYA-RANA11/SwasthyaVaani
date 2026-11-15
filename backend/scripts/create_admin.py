"""Create an admin user.

Run from the backend folder:
    python -m scripts.create_admin
"""
import getpass

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User, UserRole


def main():
    full_name = input("Admin full name: ").strip()
    email = input("Admin email: ").strip().lower()
    password = getpass.getpass("Password (min 8 chars): ")

    if len(password) < 8:
        print("Password must be at least 8 characters.")
        return

    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == email).first():
            print("A user with this email already exists.")
            return
        db.add(User(
            full_name=full_name,
            email=email,
            hashed_password=hash_password(password),
            role=UserRole.ADMIN,
        ))
        db.commit()
        print(f"Admin created: {email}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
