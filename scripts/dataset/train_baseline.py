import pandas as pd
from pathlib import Path

from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)

BASE_DIR = Path("rta-backend/data/processed/ml")

X_TRAIN_FILE = BASE_DIR / "X_train.csv"
X_TEST_FILE = BASE_DIR / "X_test.csv"
Y_TRAIN_FILE = BASE_DIR / "y_train.csv"
Y_TEST_FILE = BASE_DIR / "y_test.csv"


def main():
    print("=" * 70)
    print("TRAINING BASELINE MODEL")
    print("=" * 70)

    print("\nLoading training data...")

    X_train = pd.read_csv(X_TRAIN_FILE)
    X_test = pd.read_csv(X_TEST_FILE)

    y_train = pd.read_csv(Y_TRAIN_FILE).iloc[:, 0]
    y_test = pd.read_csv(Y_TEST_FILE).iloc[:, 0]

    print(f"Training features: {X_train.shape}")
    print(f"Testing features:  {X_test.shape}")

    print("\nTraining target distribution:")
    print(y_train.value_counts())

    print("\nCreating Logistic Regression baseline...")

    model = LogisticRegression(
        max_iter=2000,
        class_weight="balanced",
        random_state=42,
    )

    print("\nTraining model...")
    model.fit(X_train, y_train)

    print("Training completed.")

    print("\nMaking predictions...")
    y_pred = model.predict(X_test)

    print("\n" + "=" * 70)
    print("MODEL EVALUATION")
    print("=" * 70)

    accuracy = accuracy_score(y_test, y_pred)

    balanced_accuracy = balanced_accuracy_score(
        y_test,
        y_pred,
    )

    macro_f1 = f1_score(
        y_test,
        y_pred,
        average="macro",
    )

    print(f"\nAccuracy:           {accuracy:.4f}")
    print(f"Balanced Accuracy:  {balanced_accuracy:.4f}")
    print(f"Macro F1:           {macro_f1:.4f}")

    print("\nClassification Report:")

    print(
        classification_report(
            y_test,
            y_pred,
            digits=4,
            zero_division=0,
        )
    )

    print("\nConfusion Matrix:")

    labels = [
        "Slight Injury",
        "Serious Injury",
        "Fatal injury",
    ]

    cm = confusion_matrix(
        y_test,
        y_pred,
        labels=labels,
    )

    confusion_df = pd.DataFrame(
        cm,
        index=[f"Actual: {label}" for label in labels],
        columns=[f"Predicted: {label}" for label in labels],
    )

    print(confusion_df)

    print("\n" + "=" * 70)
    print("BASELINE TRAINING COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
