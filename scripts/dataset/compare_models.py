import pandas as pd
from pathlib import Path

from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.preprocessing import LabelEncoder


BASE_DIR = Path("rta-backend/data/processed/ml")

X_TRAIN_FILE = BASE_DIR / "X_train.csv"
X_TEST_FILE = BASE_DIR / "X_test.csv"
Y_TRAIN_FILE = BASE_DIR / "y_train.csv"
Y_TEST_FILE = BASE_DIR / "y_test.csv"


def evaluate_model(name, model, X_train, X_test, y_train, y_test):
    print("\n" + "=" * 80)
    print(f"TRAINING: {name}")
    print("=" * 80)

    print("\nTraining...")
    model.fit(X_train, y_train)

    print("Predicting...")
    y_pred = model.predict(X_test)

    accuracy = accuracy_score(y_test, y_pred)
    balanced_accuracy = balanced_accuracy_score(y_test, y_pred)
    macro_f1 = f1_score(
        y_test,
        y_pred,
        average="macro",
    )

    print("\nResults:")
    print(f"Accuracy:           {accuracy:.4f}")
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

    print("Confusion Matrix:")
    print(confusion_df)

    return {
        "Model": name,
        "Accuracy": accuracy,
        "Balanced Accuracy": balanced_accuracy,
        "Macro F1": macro_f1,
    }


def main():
    print("=" * 80)
    print("MODEL COMPARISON")
    print("=" * 80)

    print("\nLoading data...")

    X_train = pd.read_csv(X_TRAIN_FILE)
    X_test = pd.read_csv(X_TEST_FILE)

    y_train = pd.read_csv(Y_TRAIN_FILE).iloc[:, 0]
    y_test = pd.read_csv(Y_TEST_FILE).iloc[:, 0]

    print(f"Training data: {X_train.shape}")
    print(f"Testing data:  {X_test.shape}")

    results = []

    # ------------------------------------------------------------
    # MODEL 1: LOGISTIC REGRESSION
    # ------------------------------------------------------------

    logistic_model = LogisticRegression(
        max_iter=5000,
        class_weight="balanced",
        random_state=42,
    )

    results.append(
        evaluate_model(
            "Logistic Regression",
            logistic_model,
            X_train,
            X_test,
            y_train,
            y_test,
        )
    )

    # ------------------------------------------------------------
    # MODEL 2: RANDOM FOREST
    # ------------------------------------------------------------

    random_forest_model = RandomForestClassifier(
        n_estimators=300,
        max_depth=None,
        min_samples_split=5,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )

    results.append(
        evaluate_model(
            "Random Forest",
            random_forest_model,
            X_train,
            X_test,
            y_train,
            y_test,
        )
    )

    # ------------------------------------------------------------
    # MODEL 3: RANDOM FOREST WITHOUT CLASS WEIGHT
    # ------------------------------------------------------------

    random_forest_normal = RandomForestClassifier(
        n_estimators=300,
        max_depth=None,
        min_samples_split=5,
        min_samples_leaf=2,
        class_weight=None,
        random_state=42,
        n_jobs=-1,
    )

    results.append(
        evaluate_model(
            "Random Forest - No Class Weight",
            random_forest_normal,
            X_train,
            X_test,
            y_train,
            y_test,
        )
    )

    # ------------------------------------------------------------
    # MODEL 4: HISTOGRAM GRADIENT BOOSTING
    # ------------------------------------------------------------

    label_encoder = LabelEncoder()

    y_train_encoded = label_encoder.fit_transform(y_train)
    y_test_encoded = label_encoder.transform(y_test)

    gradient_model = HistGradientBoostingClassifier(
        max_iter=300,
        learning_rate=0.08,
        max_leaf_nodes=31,
        random_state=42,
    )

    print("\n" + "=" * 80)
    print("TRAINING: HistGradientBoosting")
    print("=" * 80)

    print("\nTraining...")

    gradient_model.fit(
        X_train,
        y_train_encoded,
    )

    print("Predicting...")

    gradient_pred_encoded = gradient_model.predict(X_test)

    gradient_pred = label_encoder.inverse_transform(
        gradient_pred_encoded
    )

    accuracy = accuracy_score(
        y_test,
        gradient_pred,
    )

    balanced_accuracy = balanced_accuracy_score(
        y_test,
        gradient_pred,
    )

    macro_f1 = f1_score(
        y_test,
        gradient_pred,
        average="macro",
    )

    print("\nResults:")
    print(f"Accuracy:           {accuracy:.4f}")
    print(f"Balanced Accuracy:  {balanced_accuracy:.4f}")
    print(f"Macro F1:           {macro_f1:.4f}")

    print("\nClassification Report:")
    print(
        classification_report(
            y_test,
            gradient_pred,
            digits=4,
            zero_division=0,
        )
    )

    cm = confusion_matrix(
        y_test,
        gradient_pred,
        labels=[
            "Slight Injury",
            "Serious Injury",
            "Fatal injury",
        ],
    )

    confusion_df = pd.DataFrame(
        cm,
        index=[
            "Actual: Slight Injury",
            "Actual: Serious Injury",
            "Actual: Fatal injury",
        ],
        columns=[
            "Predicted: Slight Injury",
            "Predicted: Serious Injury",
            "Predicted: Fatal injury",
        ],
    )

    print("Confusion Matrix:")
    print(confusion_df)

    results.append(
        {
            "Model": "HistGradientBoosting",
            "Accuracy": accuracy,
            "Balanced Accuracy": balanced_accuracy,
            "Macro F1": macro_f1,
        }
    )

    # ------------------------------------------------------------
    # FINAL COMPARISON
    # ------------------------------------------------------------

    results_df = pd.DataFrame(results)

    results_df = results_df.sort_values(
        by="Macro F1",
        ascending=False,
    )

    print("\n" + "=" * 80)
    print("MODEL COMPARISON SUMMARY")
    print("=" * 80)

    print(
        results_df.to_string(
            index=False,
            float_format=lambda x: f"{x:.4f}",
        )
    )

    results_file = BASE_DIR / "model_comparison_results.csv"

    results_df.to_csv(
        results_file,
        index=False,
    )

    print(f"\nResults saved to:")
    print(results_file)

    print("\nDone.")


if __name__ == "__main__":
    main()
