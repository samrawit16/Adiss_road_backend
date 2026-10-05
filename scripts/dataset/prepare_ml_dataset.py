import pandas as pd
from pathlib import Path


INPUT_FILE = Path(
    "rta-backend/data/processed/Addis_Ababa_RTA_Clean.csv"
)

OUTPUT_FILE = Path(
    "rta-backend/data/processed/Addis_Ababa_RTA_ML.csv"
)


def main():
    print("=" * 60)
    print("PREPARING ML DATASET")
    print("=" * 60)

    # ---------------------------------------------------------
    # Load cleaned dataset
    # ---------------------------------------------------------
    df = pd.read_csv(INPUT_FILE)

    print(f"\nInput file: {INPUT_FILE}")
    print(f"Original shape: {df.shape}")

    # Clean column names
    df.columns = df.columns.str.strip()

    # ---------------------------------------------------------
    # Process Time
    # ---------------------------------------------------------
    print("\nProcessing Time column...")

    time_parsed = pd.to_datetime(
        df["Time"].astype(str).str.strip(),
        format="%H:%M:%S",
        errors="coerce"
    )

    df["Hour"] = time_parsed.dt.hour
    df["Minute"] = time_parsed.dt.minute

    # Check whether any time values failed to parse
    failed_time = time_parsed.isna().sum()

    print(f"Time values that could not be parsed: {failed_time}")

    def classify_time(hour):
        if pd.isna(hour):
            return "Unknown"

        hour = int(hour)

        if 5 <= hour <= 11:
            return "Morning"
        elif 12 <= hour <= 16:
            return "Afternoon"
        elif 17 <= hour <= 20:
            return "Evening"
        else:
            return "Night"

    df["Time_period"] = df["Hour"].apply(classify_time)

    # Remove original Time column
    df = df.drop(columns=["Time"])

    # ---------------------------------------------------------
    # Remove outcome-leakage columns
    # ---------------------------------------------------------
    leakage_columns = [
        "Casualty_class",
        "Sex_of_casualty",
        "Age_band_of_casualty",
        "Casualty_severity",
        "Work_of_casuality",
        "Fitness_of_casuality",
        "Pedestrian_movement",
    ]

    existing_leakage_columns = [
        column
        for column in leakage_columns
        if column in df.columns
    ]

    print("\nRemoving leakage columns:")

    for column in existing_leakage_columns:
        print(f"  - {column}")

    df = df.drop(columns=existing_leakage_columns)

    # ---------------------------------------------------------
    # Verify target
    # ---------------------------------------------------------
    target = "Accident_severity"

    if target not in df.columns:
        raise ValueError(
            f"Target column '{target}' was not found."
        )

    # ---------------------------------------------------------
    # Remove rows with missing target
    # ---------------------------------------------------------
    before = len(df)

    df = df.dropna(subset=[target])

    removed = before - len(df)

    print(
        f"\nRows removed because target was missing: {removed}"
    )

    # ---------------------------------------------------------
    # Save ML dataset
    # ---------------------------------------------------------
    df.to_csv(OUTPUT_FILE, index=False)

    # ---------------------------------------------------------
    # Summary
    # ---------------------------------------------------------
    print("\n" + "=" * 60)
    print("ML DATASET READY")
    print("=" * 60)

    print(f"\nOutput file:")
    print(OUTPUT_FILE)

    print(f"\nFinal shape: {df.shape}")

    # ---------------------------------------------------------
    # Target distribution
    # ---------------------------------------------------------
    print("\nTarget distribution:")
    print(df[target].value_counts())

    print("\nTarget percentages:")

    percentages = (
        df[target]
        .value_counts(normalize=True)
        .mul(100)
        .round(2)
    )

    print(percentages)

    # ---------------------------------------------------------
    # Time distribution
    # ---------------------------------------------------------
    print("\nTime period distribution:")
    print(df["Time_period"].value_counts())

    print("\nHour distribution:")
    print(df["Hour"].value_counts().sort_index())

    # ---------------------------------------------------------
    # Final columns
    # ---------------------------------------------------------
    print("\nFinal columns:")

    for column in df.columns:
        print(f"  - {column}")

    # ---------------------------------------------------------
    # Missing values
    # ---------------------------------------------------------
    print("\nMissing values:")

    missing = df.isna().sum()
    missing = missing[missing > 0]

    if len(missing) == 0:
        print("  None")
    else:
        print(missing)

    # ---------------------------------------------------------
    # Final verification
    # ---------------------------------------------------------
    print("\nFinal dataset information:")
    print(f"Rows: {len(df)}")
    print(f"Columns: {len(df.columns)}")

    print("\nDone.")


if __name__ == "__main__":
    main()