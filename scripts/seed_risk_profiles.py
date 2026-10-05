"""Seed the hotspots table from the raw Addis Ababa RTA dataset."""
import os
import re
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.db.session import Base, SessionLocal, engine
from app.models.hotspot import Hotspot

CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "data", "Addis_Ababa_RTA_Raw.csv")

WEIGHTS = {"fatal": 10, "serious": 5, "slight": 1}

def hour_of(t: str) -> int:
    m = re.match(r"(\d{1,2}):(\d{2})", str(t))
    return int(m.group(1)) if m else -1

def build_profiles(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df["Area_accident_occured"] = df["Area_accident_occured"].replace(
        {"Rural village areasOffice areas": "Office areas", "Unknown": "Other"})
    df["Types_of_Junction"] = df["Types_of_Junction"].fillna("Unknown")
    df["Types_of_Junction"] = df["Types_of_Junction"].replace(
        {"Unknown": "Other", "Y shape": "Y shape", "with no junction": "No junction"})
    df["hour"] = df["Time"].map(hour_of)
    df = df[df["hour"] >= 0]

    sev = df["Accident_severity"].str.strip().str.lower()
    df["fatal"] = (sev == "fatal injury").astype(int)
    df["serious"] = (sev == "serious injury").astype(int)
    df["slight"] = (sev == "slight injury").astype(int)

    grouped = (df.groupby(["Area_accident_occured", "Types_of_Junction"])
                 .agg(accidents=("fatal", "size"),
                      fatalities=("fatal", "sum"),
                      injuries=("serious", "sum"),
                      peak_hour=("hour", lambda s: int(s.mode().iat[0]))))
    grouped["risk_score"] = (grouped["fatalities"] * WEIGHTS["fatal"]
                             + grouped["injuries"] * WEIGHTS["serious"]
                             + (grouped["accidents"] - grouped["fatalities"] - grouped["injuries"]) * WEIGHTS["slight"])
    grouped = grouped.sort_values("risk_score", ascending=False).reset_index()
    grouped["severity"] = grouped["risk_score"].apply(
        lambda s: "critical" if s >= 80 else "high" if s >= 30 else "medium")
    return grouped

def main() -> None:
    if not os.path.exists(CSV_PATH):
        print(f"ERROR: dataset not found at {CSV_PATH}")
        print("Put Addis_Ababa_RTA_Raw.csv in the data/ folder and try again.")
        sys.exit(1)
    Base.metadata.create_all(bind=engine)
    profiles = build_profiles(CSV_PATH)
    with SessionLocal() as db:
        db.query(Hotspot).delete()
        db.commit()
        for _, r in profiles.iterrows():
            db.add(Hotspot(area=r["Area_accident_occured"],
                           junction_type=r["Types_of_Junction"],
                           accidents=int(r["accidents"]), fatalities=int(r["fatalities"]),
                           injuries=int(r["injuries"]), risk_score=float(r["risk_score"]),
                           peak_hour=int(r["peak_hour"]), severity=r["severity"]))
        db.commit()
    print(f"Seeded {len(profiles)} risk profiles into {settings.database_url}")

if __name__ == "__main__":
    main()
