import os
import pickle
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score

# =========================
# PATHS
# =========================
BASE_DIR = os.path.dirname(__file__)

CSV_PATH = os.path.join(
    BASE_DIR,
    "data",
    "data.csv"
)

MODEL_PATH = os.path.join(
    BASE_DIR,
    "sign_classifier.pkl"
)

# =========================
# LOAD DATASET
# =========================
print("📥 Loading dataset...")

df = pd.read_csv(CSV_PATH)

print(f"Dataset size: {len(df)} samples")

# =========================
# SPLIT FEATURES + LABELS
# =========================
X = df.drop("label", axis=1)
y = df["label"]

# =========================
# TRAIN / TEST SPLIT
# =========================
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42
)

# =========================
# TRAIN MODEL
# =========================
print("\n🚀 Training model...")

model = RandomForestClassifier(
    n_estimators=200,
    random_state=42
)

model.fit(X_train, y_train)

# =========================
# TEST ACCURACY
# =========================
predictions = model.predict(X_test)

accuracy = accuracy_score(
    y_test,
    predictions
)

print(f"\n✅ Accuracy: {accuracy * 100:.2f}%")

# =========================
# SAVE MODEL
# =========================
with open(MODEL_PATH, "wb") as f:

    pickle.dump(model, f)

print(f"\n💾 Model saved:")
print(MODEL_PATH)