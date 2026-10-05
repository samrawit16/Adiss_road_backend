"""Fill the database with realistic (fictional) Addis Ababa reports for the dashboard.

    python -m scripts.seed_demo_data            # only if no demo data exists yet
    python -m scripts.seed_demo_data --reset    # wipe demo data and regenerate
    python -m scripts.seed_demo_data --clear    # remove demo data only

Demo reporters use @demo.adissroad.et emails and cannot log in. Real users and
real reports are never touched.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import base  # noqa: F401  (registers models)
from app.db.session import Base, SessionLocal, engine
from app.services.demo_seed import clear_demo_data, seed_demo_data


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--clear", action="store_true")
    parser.add_argument("--reports", type=int, default=160)
    parser.add_argument("--events", type=int, default=140)
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        if args.clear:
            clear_demo_data(db)
            print("Demo data removed.")
            return
        result = seed_demo_data(db, reports=args.reports, events=args.events, reset=args.reset)
    if result.get("skipped"):
        print("Demo data already present. Use --reset to regenerate.")
    else:
        print(f"Seeded {result['reports']} reports, {result['events']} events, {result['users']} demo reporters.")


if __name__ == "__main__":
    main()
