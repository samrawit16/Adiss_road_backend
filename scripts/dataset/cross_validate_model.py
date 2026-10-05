import pandas as pd
from pathlib import Path

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.metrics import make_scorer, f1_score, balanced_accuracy_score


BASE_DIR = Path("rta-backend/data/processed/ml")

X_TRAIN_FILE = BASE_DIR / "X_train.csv"
Y_TRAIN_FILE = BASE_DIR / "y_train.csv"


def main():
    print("=" * 80)
    print("5-FOLD STRATIFIED CROSS-VALIDATION")
    print("=" * 80)

    print("\nLoading training data...")

    X_train = pd.read_csv(X_TRAIN_FILE)
    y_train = pd.read_csv(Y_TRAIN_FILE).iloc[:, 0]

    print(f"Training features: {X_train.shape}")
    print(f"Training labels:   {y_train.shape}")

    print("\nTraining class distribution:")
    print(y_train.value_counts())

    model = RandomForestClassifier(
        n_estimators=400,
        min_samples_split=5,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )

    scoring = {
        "macro_f1": make_scorer(
            f1_score,
            average="macro",
        ),
        "balanced_accuracy": make_scorer(
            balanced_accuracy_score,
        ),
        "fatal_recall": make_scorer(
            f1_score,
            labels=["Fatal injury"],
            average=None,
        ),
    }

    cv = StratifiedKFold(
        n_splits=5,
        shuffle=True,
        random_state=42,
    )

    print("\nRunning 5-fold cross-validation...")
    print("This may take a few minutes.")

    scores = cross_validate(
        model,
        X_train,
        y_train,
        cv=cv,
        scoring=scoring,
        n_jobs=1,
        return_train_score=False,
    )

    print("\n" + "=" * 80)
    print("CROSS-VALIDATION RESULTS")
    print("=" * 80)

    print("\nMacro F1 by fold:")
    for i, value in enumerate(scores["test_macro_f1"], start=1):
        print(f"Fold {i}: {value:.4f}")

    print(
        f"\nMacro F1 mean: {scores['test_macro_f1'].mean():.4f}"
    )

    print(
        f"Macro F1 std:  {scores['test_macro_f1'].std():.4f}"
    )

    print("\nBalanced Accuracy by fold:")
    for i, value in enumerate(
        scores["test_balanced_accuracy"],
        start=1,
    ):
        print(f"Fold {i}: {value:.4f}")

    print(
        f"\nBalanced Accuracy mean: "
        f"{scores['test_balanced_accuracy'].mean():.4f}"
    )

    print(
        f"Balanced Accuracy std:  "
        f"{scores['test_balanced_accuracy'].std():.4f}"
    )

    print("\nFatal F1 by fold:")

    for i, value in enumerate(
        scores["test_fatal_recall"],
        start=1,
    ):
        print(f"Fold {i}: {value:.4f}")

    print(
        f"\nFatal F1 mean: "
        f"{scores['test_fatal_recall'].mean():.4f}"
    )

    print(
        f"Fatal F1 std:  "
        f"{scores['test_fatal_recall'].std():.4f}"
    )

    print("\n" + "=" * 80)
    print("CROSS-VALIDATION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()

