from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User

class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_email(self, email: str) -> User | None:
        return self.db.scalar(select(User).where(User.email == email.lower()))

    def get(self, user_id: int) -> User | None:
        return self.db.get(User, user_id)

    def create(self, full_name: str, email: str, phone: str, hashed_password: str) -> User:
        user = User(full_name=full_name, email=email.lower(), phone=phone,
                    hashed_password=hashed_password, is_verified=False)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
