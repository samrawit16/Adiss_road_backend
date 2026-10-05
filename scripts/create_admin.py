"""Create the default admin, or reset its password to DEFAULT_ADMIN_PASSWORD.

    python -m scripts.create_admin
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.db.session import Base, SessionLocal, engine
from app.db import base  # noqa: F401  (registers models)
from app.services.admin_bootstrap import ensure_default_admin


def main() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        user = ensure_default_admin(db, reset_password=True)
    if user is None:
        print("DEFAULT_ADMIN_EMAIL / DEFAULT_ADMIN_PASSWORD are not set; nothing done.")
        return
    print(f"Admin ready: {user.email} (password set from DEFAULT_ADMIN_PASSWORD)")
    print(f"Database: {settings.database_url.split('@')[-1]}")


if __name__ == "__main__":
    main()
