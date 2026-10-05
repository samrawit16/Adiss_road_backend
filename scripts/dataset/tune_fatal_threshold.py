import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import (
    f1_score,
    balanced_accuracy_score,
    precision_score,
    recall_score,
)


print("=" * 80)
print("FATAL CLASS THRESHOLD TUNING - 5-FOLD CROSS-VALIDATION")
print("=" * 80)


# -------------------------------------------------------------------
# Load training data
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
# Thresholds
# -------------------------------------------------------------------

thresholds = [
    0.10,
    0.15,
    0.20,
    0.25,
    0.30,
    0.35,
    0.40,
    0.45,
    0.50,
]


results = []


# -------------------------------------------------------------------
# Cross-validation
# -------------------------------------------------------------------

for threshold in thresholds:

    print(f"\nTesting Fatal threshold: {threshold:.2f}")

    fold_macro_f1 = []
    fold_balanced_accuracy = []
    fold_fatal_precision = []
    fold_fatal_recall = []
    fold_fatal_f1 = []

    for fold, (train_idx, val_idx) in enumerate(
        cv.split(X, y),
        start=1
    ):

        X_train = X.iloc[train_idx]
        X_val = X.iloc[val_idx]

        y_train = y.iloc[train_idx]
        y_val = y.iloc[val_idx]

        # -----------------------------------------------------------
        # Train model
        # -----------------------------------------------------------

        model = RandomForestClassifier(
            n_estimators=400,
            min_samples_split=5,
            min_samples_leaf=2,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1
        )

        model.fit(X_train, y_train)

        # -----------------------------------------------------------
        # Probabilities
        # -----------------------------------------------------------

        probabilities = model.predict_proba(X_val)

        classes = list(model.classes_)

        fatal_index = classes.index("Fatal injury")

        fatal_probability = probabilities[:, fatal_index]

        # -----------------------------------------------------------
        # Normal prediction
        # -----------------------------------------------------------

        predictions = np.array(
            classes
        )[np.argmax(probabilities, axis=1)]

        # -----------------------------------------------------------
        # Apply Fatal threshold
        # -----------------------------------------------------------

        fatal_mask = fatal_probability >= threshold

        predictions[fatal_mask] = "Fatal injury"

        # -----------------------------------------------------------
        # Metrics
        # -----------------------------------------------------------

        macro_f1 = f1_score(
            y_val,
            predictions,
            average="macro",
            zero_division=0
        )

        balanced_acc = balanced_accuracy_score(
            y_val,
            predictions
        )

        fatal_precision = precision_score(
            y_val,
            predictions,
            labels=["Fatal injury"],
            average="macro",
            zero_division=0
        )

        fatal_recall = recall_score(
            y_val,
            predictions,
            labels=["Fatal injury"],
            average="macro",
            zero_division=0
        )

        fatal_f1 = f1_score(
            y_val,
            predictions,
            labels=["Fatal injury"],
            average="macro",
            zero_division=0
        )

        fold_macro_f1.append(macro_f1)
        fold_balanced_accuracy.append(balanced_acc)
        fold_fatal_precision.append(fatal_precision)
        fold_fatal_recall.append(fatal_recall)
        fold_fatal_f1.append(fatal_f1)

    # ----------------------------------------------------------------
    # Average across folds
    # ----------------------------------------------------------------

    results.append({
        "Threshold": threshold,
        "Macro F1": np.mean(fold_macro_f1),
        "Balanced Accuracy": np.mean(fold_balanced_accuracy),
        "Fatal Precision": np.mean(fold_fatal_precision),
        "Fatal Recall": np.mean(fold_fatal_recall),
        "Fatal F1": np.mean(fold_fatal_f1),
    })


# -------------------------------------------------------------------
# Results
# -------------------------------------------------------------------

results_df = pd.DataFrame(results)

print("\n")
print("=" * 80)
print("THRESHOLD COMPARISON")
print("=" * 80)

print(
    results_df.to_string(
        index=False,
        float_format=lambda x: f"{x:.4f}"
    )
)


# -------------------------------------------------------------------
# Best by different metrics
# -------------------------------------------------------------------

print("\n")
print("=" * 80)
print("BEST THRESHOLDS")
print("=" * 80)

best_macro = results_df.loc[
    results_df["Macro F1"].idxmax()
]

best_balanced = results_df.loc[
    results_df["Balanced Accuracy"].idxmax()
]

best_fatal_f1 = results_df.loc[
    results_df["Fatal F1"].idxmax()
]

best_fatal_recall = results_df.loc[
    results_df["Fatal Recall"].idxmax()
]

print("\nBest Macro F1:")
print(best_macro.to_string())

print("\nBest Balanced Accuracy:")
print(best_balanced.to_string())

print("\nBest Fatal F1:")
print(best_fatal_f1.to_string())

print("\nBest Fatal Recall:")
print(best_fatal_recall.to_string())


# -------------------------------------------------------------------
# Save
# -------------------------------------------------------------------

output_path = (
    "rta-backend/data/processed/ml/"
    "fatal_threshold_results.csv"
)

results_df.to_csv(
    output_path,
    index=False
)

print("\nResults saved to:")
print(output_path)

print("\nDone.")
