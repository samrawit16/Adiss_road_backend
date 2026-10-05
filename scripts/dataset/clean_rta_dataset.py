import pandas as pd
from pathlib import Path


INPUT_FILE = Path("rta-backend/data/Addis_Ababa_RTA_Raw.csv")
OUTPUT_FILE = Path(
    "rta-backend/data/processed/Addis_Ababa_RTA_Clean.csv"
)


def main():
    print("Loading dataset...")

    df = pd.read_csv(INPUT_FILE)

    print(f"Original rows: {len(df):,}")
    print(f"Original columns: {len(df.columns)}")

    # ---------------------------------------------------------
    # 1. Remove completely duplicated accident records
    # ---------------------------------------------------------
    duplicates = df.duplicated().sum()

    print(f"Duplicate rows found: {duplicates:,}")

    df = df.drop_duplicates().copy()

    # ---------------------------------------------------------
    # 2. Clean column names
    # ---------------------------------------------------------
    df.columns = (
        df.columns
        .str.strip()
        .str.replace(" ", "_")
    )

    # ---------------------------------------------------------
    # 3. Clean string values
    # ---------------------------------------------------------
    object_columns = df.select_dtypes(include="object").columns

    for column in object_columns:
        df[column] = df[column].apply(
            lambda x: x.strip() if isinstance(x, str) else x
        )

    # ---------------------------------------------------------
    # 4. Standardize missing values
    # ---------------------------------------------------------
    missing_values = [
        "",
        " ",
        "NaN",
        "nan",
        "N/A",
        "n/a",
        "NULL",
        "null",
    ]

    df = df.replace(missing_values, pd.NA)

    # ---------------------------------------------------------
    # 5. Treat "na" as missing for casualty-specific fields
    # ---------------------------------------------------------
    casualty_columns = [
        "Casualty_class",
        "Sex_of_casualty",
        "Age_band_of_casualty",
    ]

    for column in casualty_columns:
        if column in df.columns:
            df[column] = df[column].replace("na", pd.NA)

    # ---------------------------------------------------------
    # 6. Normalize text fields
    # ---------------------------------------------------------
    for column in object_columns:
        if column in df.columns:
            df[column] = df[column].apply(
                lambda x: x.strip() if isinstance(x, str) else x
            )

    # ---------------------------------------------------------
    # 7. Validate numeric columns
    # ---------------------------------------------------------
    numeric_columns = [
        "Number_of_vehicles_involved",
        "Number_of_casualties",
    ]

    for column in numeric_columns:
        if column in df.columns:
            df[column] = pd.to_numeric(
                df[column],
                errors="coerce"
            )

    # ---------------------------------------------------------
    # 8. Remove impossible numeric values
    # ---------------------------------------------------------
    if "Number_of_vehicles_involved" in df.columns:
        df = df[
            df["Number_of_vehicles_involved"].notna()
            & (df["Number_of_vehicles_involved"] > 0)
        ]

    if "Number_of_casualties" in df.columns:
        df = df[
            df["Number_of_casualties"].notna()
            & (df["Number_of_casualties"] >= 0)
        ]

    # ---------------------------------------------------------
    # 9. Normalize accident severity
    # ---------------------------------------------------------
    if "Accident_severity" in df.columns:
        df["Accident_severity"] = (
            df["Accident_severity"]
            .astype("string")
            .str.strip()
        )

    # ---------------------------------------------------------
    # 10. Save cleaned dataset
    # ---------------------------------------------------------
    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print()
    print("=" * 60)
    print("CLEANING COMPLETE")
    print("=" * 60)
    print(f"Final rows: {len(df):,}")
    print(f"Final columns: {len(df.columns)}")
    print(f"Output: {OUTPUT_FILE}")

    print()
    print("Accident severity:")
    print(df["Accident_severity"].value_counts(dropna=False))

    print()
    print("Remaining missing values:")
    print(
        df.isna()
        .sum()
        .sort_values(ascending=False)
        .head(15)
    )


if __name__ == "__main__":
    main()
