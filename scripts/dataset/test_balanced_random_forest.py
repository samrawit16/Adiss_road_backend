import pandas as pd

from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.metrics import (
    f1_score,
    balanced_accuracy_score,
    recall_score,
    make_scorer,
)

from imblearn.ensemble import BalancedRandomForestClassifier


print("=" * 80)
print("BALANCED RANDOM FOREST - 5-FOLD CROSS-VALIDATION")
print("=" * 80)

# -------------------------------------------------------------------
# Load data
# -------------------------------------------------------------------

print("\nLoading training data...")

X = pd.read_csv(
    "rta-backend/data/processed/ml/X_train.csv"
)

y = pd.read_csv(
    "rta-backend/data/processed/ml/y_train.csv"
).squeeze()

print(f"Training features: {X.shape}")
print(f"Training labels:   {y.shape}")

print("\nClass distribution:")
print(y.value_counts())


# -------------------------------------------------------------------
# Cross-validation
# -------------------------------------------------------------------

cv = StratifiedKFold(
    n_splits=5,
    shuffle=True,
    random_state=42
)


# -------------------------------------------------------------------
# Metrics
# -------------------------------------------------------------------

scoring = {
    "macro_f1": make_scorer(
        f1_score,
        average="macro",
        zero_division=0
    ),

    "balanced_accuracy": make_scorer(
        balanced_accuracy_score
    ),

    "fatal_f1": make_scorer(
        f1_score,
        labels=["Fatal injury"],
        average="macro",
        zero_division=0
    ),

    "fatal_recall": make_scorer(
        recall_score,
        labels=["Fatal injury"],
        average="macro",
        zero_division=0
    ),
}


# -------------------------------------------------------------------
# Balanced Random Forest
# -------------------------------------------------------------------

model = BalancedRandomForestClassifier(
    n_estimators=400,
    max_depth=None,
    min_samples_split=5,
    min_samples_leaf=2,
    random_state=42,
    n_jobs=-1
)


# -------------------------------------------------------------------
# Cross-validation
# -------------------------------------------------------------------

print("\nRunning 5-fold cross-validation...")
print("This may take a few minutes.")

scores = cross_validate(
    model,
    X,
    y,
    cv=cv,
    scoring=scoring,
    n_jobs=1
)


# -------------------------------------------------------------------
# Results
# -------------------------------------------------------------------

macro_f1_mean = scores["test_macro_f1"].mean()
macro_f1_std = scores["test_macro_f1"].std()

balanced_acc_mean = scores["test_balanced_accuracy"].mean()
balanced_acc_std = scores["test_balanced_accuracy"].std()

fatal_f1_mean = scores["test_fatal_f1"].mean()
fatal_f1_std = scores["test_fatal_f1"].std()

fatal_recall_mean = scores["test_fatal_recall"].mean()
fatal_recall_std = scores["test_fatal_recall"].std()


print("\n")
print("=" * 80)
print("BALANCED RANDOM FOREST RESULTS")
print("=" * 80)

print(
    f"\nMacro F1:          "
    f"{macro_f1_mean:.4f} ± {macro_f1_std:.4f}"
)

print(
    f"Balanced Accuracy: "
    f"{balanced_acc_mean:.4f} ± {balanced_acc_std:.4f}"
)

print(
    f"Fatal F1:          "
    f"{fatal_f1_mean:.4f} ± {fatal_f1_std:.4f}"
)

print(
    f"Fatal Recall:      "
    f"{fatal_recall_mean:.4f} ± {fatal_recall_std:.4f}"
)


# -------------------------------------------------------------------
# Fold results
# -------------------------------------------------------------------

print("\n" + "=" * 80)
print("FOLD RESULTS")
print("=" * 80)

for i in range(5):

    print(
        f"\nFold {i + 1}:"
        f"\n  Macro F1:          {scores['test_macro_f1'][i]:.4f}"
        f"\n  Balanced Accuracy: {scores['test_balanced_accuracy'][i]:.4f}"
        f"\n  Fatal F1:          {scores['test_fatal_f1'][i]:.4f}"
        f"\n  Fatal Recall:      {scores['test_fatal_recall'][i]:.4f}"
    )


print("\n")
print("=" * 80)
print("BALANCED RANDOM FOREST TEST COMPLETE")
print("=" * 80)
