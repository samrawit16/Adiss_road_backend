import pandas as pd
from pathlib import Path

from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder


# ---------------------------------------------------------
# Paths
# ---------------------------------------------------------
INPUT_FILE = Path(
    "rta-backend/data/processed/Addis_Ababa_RTA_ML.csv"
)

OUTPUT_DIR = Path(
    "rta-backend/data/processed/ml"
)


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------
TARGET = "Accident_severity"

TEST_SIZE = 0.20

RANDOM_STATE = 42


def main():
    print("=" * 70)
    print("PREPARING TRAIN / TEST DATA")
    print("=" * 70)

    # -----------------------------------------------------
    # Load dataset
    # -----------------------------------------------------
    df = pd.read_csv(INPUT_FILE)

    print("\nInput dataset:")
    print(f"Rows:    {len(df)}")
    print(f"Columns: {len(df.columns)}")

    # -----------------------------------------------------
    # Separate target
    # -----------------------------------------------------
    if TARGET not in df.columns:
        raise ValueError(
            f"Target column '{TARGET}' was not found."
        )

    y = df[TARGET].copy()

    X = df.drop(columns=[TARGET]).copy()

    # -----------------------------------------------------
    # Remove post-accident feature
    # -----------------------------------------------------
    post_accident_features = [
        "Number_of_casualties"
    ]

    existing_post_accident = [
        column
        for column in post_accident_features
        if column in X.columns
    ]

    print("\nRemoving post-accident features:")

    for column in existing_post_accident:
        print(f"  - {column}")

    X = X.drop(columns=existing_post_accident)

    # -----------------------------------------------------
    # Identify feature types
    # -----------------------------------------------------
    categorical_features = X.select_dtypes(
        include=["object", "string", "category"]
    ).columns.tolist()

    numeric_features = X.select_dtypes(
        include=["number"]
    ).columns.tolist()

    print("\nCategorical features:")
    print(f"Count: {len(categorical_features)}")

    for column in categorical_features:
        print(f"  - {column}")

    print("\nNumeric features:")
    print(f"Count: {len(numeric_features)}")

    for column in numeric_features:
        print(f"  - {column}")

    # -----------------------------------------------------
    # Create preprocessing pipelines
    # -----------------------------------------------------
    categorical_pipeline = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(
                    strategy="most_frequent"
                )
            ),
            (
                "encoder",
                OneHotEncoder(
                    handle_unknown="ignore",
                    sparse_output=False
                )
            ),
        ]
    )

    numeric_pipeline = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(
                    strategy="median"
                )
            )
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            (
                "categorical",
                categorical_pipeline,
                categorical_features,
            ),
            (
                "numeric",
                numeric_pipeline,
                numeric_features,
            ),
        ]
    )

    # -----------------------------------------------------
    # Train / test split
    # -----------------------------------------------------
    print("\nSplitting dataset...")

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=y,
    )

    print(
        f"Training rows: {len(X_train)}"
    )

    print(
        f"Testing rows:  {len(X_test)}"
    )

    # -----------------------------------------------------
    # Check class distribution
    # -----------------------------------------------------
    print("\nTraining target distribution:")
    print(y_train.value_counts())

    print("\nTraining target percentages:")
    print(
        y_train
        .value_counts(normalize=True)
        .mul(100)
        .round(2)
    )

    print("\nTesting target distribution:")
    print(y_test.value_counts())

    print("\nTesting target percentages:")
    print(
        y_test
        .value_counts(normalize=True)
        .mul(100)
        .round(2)
    )

    # -----------------------------------------------------
    # Fit preprocessing ONLY on training data
    # -----------------------------------------------------
    print("\nFitting preprocessing pipeline...")

    X_train_processed = preprocessor.fit_transform(
        X_train
    )

    X_test_processed = preprocessor.transform(
        X_test
    )

    print(
        f"Processed training shape: "
        f"{X_train_processed.shape}"
    )

    print(
        f"Processed testing shape: "
        f"{X_test_processed.shape}"
    )

    # -----------------------------------------------------
    # Get feature names
    # -----------------------------------------------------
    feature_names = (
        preprocessor
        .get_feature_names_out()
    )

    print(
        f"\nFinal feature count: "
        f"{len(feature_names)}"
    )

    # -----------------------------------------------------
    # Convert processed arrays to DataFrames
    # -----------------------------------------------------
    X_train_processed = pd.DataFrame(
        X_train_processed,
        columns=feature_names,
        index=X_train.index,
    )

    X_test_processed = pd.DataFrame(
        X_test_processed,
        columns=feature_names,
        index=X_test.index,
    )

    # -----------------------------------------------------
    # Reset indexes
    # -----------------------------------------------------
    X_train_processed = X_train_processed.reset_index(
        drop=True
    )

    X_test_processed = X_test_processed.reset_index(
        drop=True
    )

    y_train = y_train.reset_index(drop=True)
    y_test = y_test.reset_index(drop=True)

    # -----------------------------------------------------
    # Create output directory
    # -----------------------------------------------------
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # -----------------------------------------------------
    # Save datasets
    # -----------------------------------------------------
    X_train_processed.to_csv(
        OUTPUT_DIR / "X_train.csv",
        index=False
    )

    X_test_processed.to_csv(
        OUTPUT_DIR / "X_test.csv",
        index=False
    )

    y_train.to_csv(
        OUTPUT_DIR / "y_train.csv",
        index=False
    )

    y_test.to_csv(
        OUTPUT_DIR / "y_test.csv",
        index=False
    )

    # -----------------------------------------------------
    # Save feature names
    # -----------------------------------------------------
    pd.DataFrame({
        "feature": feature_names
    }).to_csv(
        OUTPUT_DIR / "feature_names.csv",
        index=False
    )

    # -----------------------------------------------------
    # Final summary
    # -----------------------------------------------------
    print("\n" + "=" * 70)
    print("TRAIN / TEST DATA READY")
    print("=" * 70)

    print("\nFiles created:")

    print(
        f"  - {OUTPUT_DIR / 'X_train.csv'}"
    )

    print(
        f"  - {OUTPUT_DIR / 'X_test.csv'}"
    )

    print(
        f"  - {OUTPUT_DIR / 'y_train.csv'}"
    )

    print(
        f"  - {OUTPUT_DIR / 'y_test.csv'}"
    )

    print(
        f"  - {OUTPUT_DIR / 'feature_names.csv'}"
    )

    print("\nDone.")


if __name__ == "__main__":
    main()
