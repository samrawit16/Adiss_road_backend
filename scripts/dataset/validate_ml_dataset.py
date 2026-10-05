import pandas as pd
from pathlib import Path


INPUT_FILE = Path(
    "rta-backend/data/processed/Addis_Ababa_RTA_ML.csv"
)


def main():
    print("=" * 70)
    print("ML DATASET VALIDATION")
    print("=" * 70)

    # ---------------------------------------------------------
    # Load dataset
    # ---------------------------------------------------------
    df = pd.read_csv(INPUT_FILE)

    print("\nDataset:")
    print(f"Rows:    {df.shape[0]}")
    print(f"Columns: {df.shape[1]}")

    # ---------------------------------------------------------
    # 1. Duplicate rows
    # ---------------------------------------------------------
    print("\n" + "=" * 70)
    print("1. DUPLICATES")
    print("=" * 70)

    duplicates = df.duplicated().sum()

    print(f"Duplicate rows: {duplicates}")

    # ---------------------------------------------------------
    # 2. Data types
    # ---------------------------------------------------------
    print("\n" + "=" * 70)
    print("2. DATA TYPES")
    print("=" * 70)

    print(df.dtypes)

    # ---------------------------------------------------------
    # 3. Missing values
    # ---------------------------------------------------------
    print("\n" + "=" * 70)
    print("3. MISSING VALUES")
    print("=" * 70)

    missing = df.isna().sum()
    missing_percent = (
        df.isna().mean() * 100
    ).round(2)

    missing_table = pd.DataFrame({
        "Missing": missing,
        "Percentage": missing_percent
    })

    missing_table = missing_table[
        missing_table["Missing"] > 0
    ].sort_values(
        "Missing",
        ascending=False
    )

    if missing_table.empty:
        print("No missing values.")
    else:
        print(missing_table)

    # ---------------------------------------------------------
    # 4. Target distribution
    # ---------------------------------------------------------
    print("\n" + "=" * 70)
    print("4. TARGET DISTRIBUTION")
    print("=" * 70)

    target = "Accident_severity"

    target_counts = df[target].value_counts()
    target_percent = (
        df[target]
        .value_counts(normalize=True)
        .mul(100)
        .round(2)
    )

    target_table = pd.DataFrame({
        "Count": target_counts,
        "Percentage": target_percent
    })

    print(target_table)

    # ---------------------------------------------------------
    # 5. Categorical columns
    # ---------------------------------------------------------
    print("\n" + "=" * 70)
    print("5. CATEGORICAL COLUMNS")
    print("=" * 70)

    categorical_columns = df.select_dtypes(
        include=["object", "string", "category"]
    ).columns

    print(f"\nNumber of categorical columns: {len(categorical_columns)}")

    for column in categorical_columns:
        print(f"\n--- {column} ---")
        print(f"Unique values: {df[column].nunique(dropna=True)}")

        values = df[column].value_counts(
            dropna=False
        ).head(15)

        print(values)

    # ---------------------------------------------------------
    # 6. Numeric columns
    # ---------------------------------------------------------
    print("\n" + "=" * 70)
    print("6. NUMERIC COLUMNS")
    print("=" * 70)

    numeric_columns = df.select_dtypes(
        include=["number"]
    ).columns

    print("\nNumeric columns:")

    for column in numeric_columns:
        print(
            f"\n--- {column} ---"
        )

        print(
            df[column].describe()
        )

    # ---------------------------------------------------------
    # 7. Check target leakage candidates
    # ---------------------------------------------------------
    print("\n" + "=" * 70)
    print("7. POTENTIAL POST-ACCIDENT FEATURES")
    print("=" * 70)

    potential_post_accident = [
        "Number_of_casualties"
    ]

    for column in potential_post_accident:
        if column in df.columns:
            print(
                f"WARNING: {column} may contain "
                "information only known after an accident."
            )

    # ---------------------------------------------------------
    # 8. Check constant columns
    # ---------------------------------------------------------
    print("\n" + "=" * 70)
    print("8. CONSTANT COLUMNS")
    print("=" * 70)

    constant_columns = [
        column
        for column in df.columns
        if df[column].nunique(dropna=False) <= 1
    ]

    if constant_columns:
        print("Constant columns:")
        for column in constant_columns:
            print(f"  - {column}")
    else:
        print("No constant columns.")

    # ---------------------------------------------------------
    # 9. Check suspicious time values
    # ---------------------------------------------------------
    print("\n" + "=" * 70)
    print("9. TIME VALIDATION")
    print("=" * 70)

    print(
        f"Hour minimum: {df['Hour'].min()}"
    )

    print(
        f"Hour maximum: {df['Hour'].max()}"
    )

    print(
        f"Minute minimum: {df['Minute'].min()}"
    )

    print(
        f"Minute maximum: {df['Minute'].max()}"
    )

    invalid_hours = df[
        (df["Hour"] < 0) |
        (df["Hour"] > 23)
    ]

    invalid_minutes = df[
        (df["Minute"] < 0) |
        (df["Minute"] > 59)
    ]

    print(
        f"Invalid hours: {len(invalid_hours)}"
    )

    print(
        f"Invalid minutes: {len(invalid_minutes)}"
    )

    # ---------------------------------------------------------
    # 10. Final summary
    # ---------------------------------------------------------
    print("\n" + "=" * 70)
    print("VALIDATION COMPLETE")
    print("=" * 70)

    print(f"\nRows: {len(df)}")
    print(f"Columns: {len(df.columns)}")
    print(f"Duplicates: {duplicates}")

    print("\nDone.")


if __name__ == "__main__":
    main()
