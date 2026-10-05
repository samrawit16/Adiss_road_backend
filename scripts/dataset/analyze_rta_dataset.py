import pandas as pd
from pathlib import Path


INPUT_FILE = Path(
    "rta-backend/data/processed/Addis_Ababa_RTA_Clean.csv"
)


def analyze_column(df, column):
    if column not in df.columns:
        return

    print()
    print("=" * 60)
    print(column)
    print("=" * 60)

    print(
        df[column]
        .value_counts(dropna=False)
        .head(20)
    )


def main():
    df = pd.read_csv(INPUT_FILE)

    print("=" * 60)
    print("ADDIS ABABA ROAD TRAFFIC ACCIDENT ANALYSIS")
    print("=" * 60)

    print(f"Rows: {len(df):,}")
    print(f"Columns: {len(df.columns)}")

    important_columns = [
        "Accident_severity",
        "Cause_of_accident",
        "Weather_conditions",
        "Light_conditions",
        "Road_surface_conditions",
        "Road_surface_type",
        "Types_of_Junction",
        "Road_allignment",
        "Area_accident_occured",
        "Type_of_collision",
        "Vehicle_movement",
        "Day_of_week",
        "Time",
        "Driving_experience",
        "Age_band_of_driver",
        "Number_of_vehicles_involved",
        "Number_of_casualties",
    ]

    for column in important_columns:
        analyze_column(df, column)


if __name__ == "__main__":
    main()
