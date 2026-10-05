import os
import joblib
import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    f1_score,
    classification_report,
    confusion_matrix,
)


print("=" * 80)
print("AA GUARDIAN - FINAL ACCIDENT SEVERITY MODEL")
print("=" * 80)


# -------------------------------------------------------------------
# 1. Load ML dataset
# -------------------------------------------------------------------

DATA_PATH = (
    "rta-backend/data/processed/"
    "Addis_Ababa_RTA_ML.csv"
)

MODEL_DIR = "rta-backend/models"

MODEL_PATH = (
    f"{MODEL_DIR}/aa_guardian_severity_model.joblib"
)

os.makedirs(MODEL_DIR, exist_ok=True)

print("\nLoading dataset...")

df = pd.read_csv(DATA_PATH)

print(f"Dataset shape: {df.shape}")


# -------------------------------------------------------------------
# 2. Separate target
# -------------------------------------------------------------------

TARGET = "Accident_severity"

y = df[TARGET].copy()

X = df.drop(columns=[TARGET])


# -------------------------------------------------------------------
# 3. Remove information that is not appropriate for prediction
# -------------------------------------------------------------------

# Number_of_casualties is known after an accident and therefore
# should not be used as a predictive input.

if "Number_of_casualties" in X.columns:

    X = X.drop(
        columns=["Number_of_casualties"]
    )

    print(
        "\nRemoved post-accident feature:"
        " Number_of_casualties"
    )


print(f"\nFinal input features: {X.shape}")


# -------------------------------------------------------------------
# 4. Identify feature types
# -------------------------------------------------------------------

categorical_features = X.select_dtypes(
    include=["object"]
).columns.tolist()

numeric_features = X.select_dtypes(
    include=["int64", "float64"]
).columns.tolist()

print(
    f"\nCategorical features: {len(categorical_features)}"
)

print(
    f"Numeric features:     {len(numeric_features)}"
)


# -------------------------------------------------------------------
# 5. Preprocessing
# -------------------------------------------------------------------

categorical_pipeline = Pipeline([
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
])


numeric_pipeline = Pipeline([
    (
        "imputer",
        SimpleImputer(
            strategy="median"
        )
    )
])


preprocessor = ColumnTransformer([
    (
        "categorical",
        categorical_pipeline,
        categorical_features
    ),

    (
        "numeric",
        numeric_pipeline,
        numeric_features
    ),
])


# -------------------------------------------------------------------
# 6. Random Forest
# -------------------------------------------------------------------

classifier = RandomForestClassifier(
    n_estimators=400,
    min_samples_split=5,
    min_samples_leaf=2,
    class_weight="balanced",
    random_state=42,
    n_jobs=-1
)


# -------------------------------------------------------------------
# 7. Complete pipeline
# -------------------------------------------------------------------

model = Pipeline([
    (
        "preprocessor",
        preprocessor
    ),

    (
        "classifier",
        classifier
    ),
])


# -------------------------------------------------------------------
# 8. Train/test split
# -------------------------------------------------------------------

print("\nCreating final train/test split...")

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42,
    stratify=y
)

print(f"Training rows: {len(X_train)}")
print(f"Testing rows:  {len(X_test)}")


print("\nTraining class distribution:")
print(y_train.value_counts())

print("\nTesting class distribution:")
print(y_test.value_counts())


# -------------------------------------------------------------------
# 9. Train
# -------------------------------------------------------------------

print("\nTraining final Random Forest...")
print("This may take a few minutes.")

model.fit(
    X_train,
    y_train
)

print("Training complete.")


# -------------------------------------------------------------------
# 10. Normal predictions
# -------------------------------------------------------------------

print("\nGenerating predictions...")

probabilities = model.predict_proba(X_test)

classes = list(
    model.named_steps["classifier"].classes_
)

fatal_index = classes.index(
    "Fatal injury"
)

fatal_probabilities = probabilities[
    :, fatal_index
]


# -------------------------------------------------------------------
# 11. Apply Fatal threshold = 0.25
# -------------------------------------------------------------------

FATAL_THRESHOLD = 0.25

predictions = np.array(
    classes
)[np.argmax(probabilities, axis=1)]


fatal_mask = (
    fatal_probabilities >= FATAL_THRESHOLD
)

predictions[fatal_mask] = "Fatal injury"


# -------------------------------------------------------------------
# 12. Evaluate
# -------------------------------------------------------------------

accuracy = accuracy_score(
    y_test,
    predictions
)

balanced_accuracy = balanced_accuracy_score(
    y_test,
    predictions
)

macro_f1 = f1_score(
    y_test,
    predictions,
    average="macro",
    zero_division=0
)


print("\n")
print("=" * 80)
print("FINAL MODEL TEST RESULTS")
print("=" * 80)

print(
    f"\nAccuracy:           {accuracy:.4f}"
)

print(
    f"Balanced Accuracy:  {balanced_accuracy:.4f}"
)

print(
    f"Macro F1:           {macro_f1:.4f}"
)

print(
    f"Fatal Threshold:    {FATAL_THRESHOLD:.2f}"
)


# -------------------------------------------------------------------
# 13. Classification report
# -------------------------------------------------------------------

print("\nClassification Report:")

print(
    classification_report(
        y_test,
        predictions,
        zero_division=0
    )
)


# -------------------------------------------------------------------
# 14. Confusion matrix
# -------------------------------------------------------------------

print("\nConfusion Matrix:")

labels = [
    "Fatal injury",
    "Serious Injury",
    "Slight Injury",
]

cm = confusion_matrix(
    y_test,
    predictions,
    labels=labels
)

cm_df = pd.DataFrame(
    cm,
    index=[
        f"Actual {label}"
        for label in labels
    ],
    columns=[
        f"Predicted {label}"
        for label in labels
    ]
)

print(cm_df)


# -------------------------------------------------------------------
# 15. Save model
# -------------------------------------------------------------------

print("\nSaving model...")

joblib.dump(
    {
        "model": model,
        "fatal_threshold": FATAL_THRESHOLD,
        "classes": classes,
        "feature_names": list(X.columns),
        "target_name": TARGET,
    },
    MODEL_PATH
)

print(
    f"\nModel saved to:\n{MODEL_PATH}"
)


# -------------------------------------------------------------------
# 16. Verify saved model
# -------------------------------------------------------------------

print("\nVerifying saved model...")

loaded = joblib.load(
    MODEL_PATH
)

print(
    "Loaded successfully."
)

print(
    f"Model classes: {loaded['classes']}"
)

print(
    f"Fatal threshold: {loaded['fatal_threshold']}"
)

print(
    f"Input features: {len(loaded['feature_names'])}"
)


print("\n")
print("=" * 80)
print("FINAL MODEL TRAINING COMPLETE")
print("=" * 80)
