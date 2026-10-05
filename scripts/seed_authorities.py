"""Seed the verified Addis Ababa authority registry for local development."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import Base, SessionLocal, engine
from app.models.safety import Authority

DEFAULT_AUTHORITIES = [
    {
        "name": "Addis Ababa Police Commission",
        "authority_type": "police",
        "phone": "991",
        "email": None,
        "latitude": 9.03,
        "longitude": 38.74,
        "coverage_area": "Addis Ababa",
        "is_active": True,
    },
    {
        "name": "Federal Police",
        "authority_type": "police",
        "phone": "915",
        "email": None,
        "latitude": 9.025,
        "longitude": 38.755,
        "coverage_area": "Addis Ababa",
        "is_active": True,
    },
    {
        "name": "Fire and Emergency Service",
        "authority_type": "fire_emergency",
        "phone": "912",
        "email": None,
        "latitude": 9.015,
        "longitude": 38.745,
        "coverage_area": "Addis Ababa",
        "is_active": True,
    },
    {
        "name": "Red Cross Emergency Support",
        "authority_type": "medical_support",
        "phone": "907",
        "email": None,
        "latitude": 9.02,
        "longitude": 38.73,
        "coverage_area": "Addis Ababa",
        "is_active": True,
    },
]


def main():
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        if db.query(Authority).count() == 0:
            db.add_all([Authority(**item) for item in DEFAULT_AUTHORITIES])
            db.commit()
            print(f"Seeded {len(DEFAULT_AUTHORITIES)} Addis Ababa authority records.")
        else:
            print("Authorities already exist; no changes made.")


if __name__ == "__main__":
    main()
