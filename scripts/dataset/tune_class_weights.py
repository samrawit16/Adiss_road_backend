import pandas as pd
from pathlib import Path

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    f1_score,
)


BASE_DIR = Path("rta-backend/data/processed/ml")

X_TRAIN_FILE = BASE_DIR / "X_train.csv"
X_TEST_FILE = BASE_DIR / "X_test.csv"
Y_TRAIN_FILE = BASE_DIR / "y_train.csv"
Y_TEST_FILE = BASE_DIR / "y_test.csv"


CLASS_WEIGHT_CONFIGS = {
    "balanced": "balanced",

    "moderate_fatal": {
        "Slight Injury": 1.0,
        "Serious Injury": 2.0,
        "Fatal injury": 5.0,
    },

    "strong_fatal": {
        "Slight Injury": 1.0,
        "Serious Injury": 3.0,
        "Fatal injury": 10.0,
    },

    "very_strong_fatal": {
        "Slight Injury": 1.0,
        "Serious Injury": 4.0,
        "Fatal injury": 15.0,
    },

    "balanced_custom": {
        "Slight Injury": 1.0,
        "Serious Injury": 4.0,
        "Fatal injury": 20.0,
    },
}


def evaluate_model(name, class_weight, X_train, X_test, y_train, y_test):
    print("\n" + "=" * 80)
    print(f"CLASS WEIGHT EXPERIMENT: {name}")
    print("=" * 80)

    print("\nClass weights:")
    print(class_weight)

    model = RandomForestClassifier(
        n_estimators=400,
        min_samples_split=5,
        min_samples_leaf=2,
        class_weight=class_weight,
        random_state=42,
        n_jobs=-1,
    )

    print("\nTraining...")
    model.fit(X_train, y_train)

    print("Predicting...")
    y_pred = model.predict(X_test)

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

    report = classification_report(
        y_test,
        y_pred,
        labels=[
            "Slight Injury",
            "Serious Injury",
            "Fatal injury",
        ],
        output_dict=True,
        zero_division=0,
    )

    fatal_recall = report["Fatal injury"]["recall"]
    serious_recall = report["Serious Injury"]["recall"]
    slight_recall = report["Slight Injury"]["recall"]

    fatal_f1 = report["Fatal injury"]["f1-score"]
    serious_f1 = report["Serious Injury"]["f1-score"]
    slight_f1 = report["Slight Injury"]["f1-score"]

    print("\nResults:")
    print(f"Accuracy:           {accuracy:.4f}")
    print(f"Balanced Accuracy:  {balanced_accuracy:.4f}")
    print(f"Macro F1:           {macro_f1:.4f}")

    print("\nClass recall:")
    print(f"Slight recall:      {slight_recall:.4f}")
    print(f"Serious recall:     {serious_recall:.4f}")
    print(f"Fatal recall:       {fatal_recall:.4f}")

    print("\nClass F1:")
    print(f"Slight F1:          {slight_f1:.4f}")
    print(f"Serious F1:         {serious_f1:.4f}")
    print(f"Fatal F1:           {fatal_f1:.4f}")

    print("\nClassification Report:")
    print(
        classification_report(
            y_test,
            y_pred,
            digits=4,
            zero_division=0,
        )
    )

    return {
        "Experiment": name,
        "Accuracy": accuracy,
        "Balanced Accuracy": balanced_accuracy,
        "Macro F1": macro_f1,
        "Slight Recall": slight_recall,
        "Serious Recall": serious_recall,
        "Fatal Recall": fatal_recall,
        "Slight F1": slight_f1,
        "Serious F1": serious_f1,
        "Fatal F1": fatal_f1,
    }


def main():
    print("=" * 80)
    print("RANDOM FOREST CLASS-WEIGHT TUNING")
    print("=" * 80)

    print("\nLoading data...")

    X_train = pd.read_csv(X_TRAIN_FILE)
    X_test = pd.read_csv(X_TEST_FILE)

    y_train = pd.read_csv(Y_TRAIN_FILE).iloc[:, 0]
    y_test = pd.read_csv(Y_TEST_FILE).iloc[:, 0]

    print(f"Training data: {X_train.shape}")
    print(f"Testing data:  {X_test.shape}")

    results = []

    for name, class_weight in CLASS_WEIGHT_CONFIGS.items():

        result = evaluate_model(
            name,
            class_weight,
            X_train,
            X_test,
            y_train,
            y_test,
        )

        results.append(result)

    results_df = pd.DataFrame(results)

    results_df = results_df.sort_values(
        by="Macro F1",
        ascending=False,
    )

    output_file = BASE_DIR / "class_weight_results.csv"

    results_df.to_csv(
        output_file,
        index=False,
    )

    print("\n" + "=" * 80)
    print("CLASS WEIGHT COMPARISON")
    print("=" * 80)

    print(
        results_df.to_string(
            index=False,
            float_format=lambda x: f"{x:.4f}",
        )
    )

    print("\nResults saved to:")
    print(output_file)

    print("\nDone.")


if __name__ == "__main__":
    main()
