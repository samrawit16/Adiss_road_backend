import pandas as pd

from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.metrics import (
    f1_score,
    balanced_accuracy_score,
    recall_score,
    make_scorer,
)


print("=" * 80)
print("ADVANCED MODEL COMPARISON - 5-FOLD CROSS-VALIDATION")
print("=" * 80)

# -------------------------------------------------------------------
# Load training data
# -------------------------------------------------------------------

print("\nLoading training data...")

data_path = "rta-backend/data/processed/ml/X_train.csv"
target_path = "rta-backend/data/processed/ml/y_train.csv"

X = pd.read_csv(data_path)
y = pd.read_csv(target_path).squeeze()

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
# Scoring
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
# Models
# -------------------------------------------------------------------

models = {

    "Random Forest": RandomForestClassifier(
        n_estimators=400,
        min_samples_split=5,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1
    ),

    "Extra Trees": ExtraTreesClassifier(
        n_estimators=400,
        min_samples_split=5,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1
    ),
}


# -------------------------------------------------------------------
# Run experiments
# -------------------------------------------------------------------

results = []

for name, model in models.items():

    print("\n" + "=" * 80)
    print(f"MODEL: {name}")
    print("=" * 80)

    print("\nTraining with 5-fold cross-validation...")

    scores = cross_validate(
        model,
        X,
        y,
        cv=cv,
        scoring=scoring,
        n_jobs=1
    )

    macro_f1_mean = scores["test_macro_f1"].mean()
    macro_f1_std = scores["test_macro_f1"].std()

    balanced_acc_mean = scores["test_balanced_accuracy"].mean()
    balanced_acc_std = scores["test_balanced_accuracy"].std()

    fatal_f1_mean = scores["test_fatal_f1"].mean()
    fatal_f1_std = scores["test_fatal_f1"].std()

    fatal_recall_mean = scores["test_fatal_recall"].mean()
    fatal_recall_std = scores["test_fatal_recall"].std()

    print("\nResults:")

    print(
        f"Macro F1:             "
        f"{macro_f1_mean:.4f} ± {macro_f1_std:.4f}"
    )

    print(
        f"Balanced Accuracy:    "
        f"{balanced_acc_mean:.4f} ± {balanced_acc_std:.4f}"
    )

    print(
        f"Fatal F1:             "
        f"{fatal_f1_mean:.4f} ± {fatal_f1_std:.4f}"
    )

    print(
        f"Fatal Recall:         "
        f"{fatal_recall_mean:.4f} ± {fatal_recall_std:.4f}"
    )

    results.append({
        "Model": name,
        "Macro F1": macro_f1_mean,
        "Macro F1 Std": macro_f1_std,
        "Balanced Accuracy": balanced_acc_mean,
        "Balanced Accuracy Std": balanced_acc_std,
        "Fatal F1": fatal_f1_mean,
        "Fatal F1 Std": fatal_f1_std,
        "Fatal Recall": fatal_recall_mean,
        "Fatal Recall Std": fatal_recall_std,
    })


# -------------------------------------------------------------------
# Comparison
# -------------------------------------------------------------------

results_df = pd.DataFrame(results)

print("\n")
print("=" * 80)
print("FINAL MODEL COMPARISON")
print("=" * 80)

print(
    results_df.to_string(
        index=False,
        float_format=lambda x: f"{x:.4f}"
    )
)

output_path = (
    "rta-backend/data/processed/ml/"
    "advanced_model_comparison.csv"
)

results_df.to_csv(output_path, index=False)

print("\nResults saved to:")
print(output_path)

print("\nDone.")
