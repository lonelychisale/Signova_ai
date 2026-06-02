import os
import pickle
import pandas as pd
import numpy as np

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score

# =========================
# PATHS
# =========================
BASE_DIR = os.path.dirname(__file__)

CSV_PATH = os.path.join(BASE_DIR, "data", "data.csv")

MODEL_PATH = os.path.join(BASE_DIR, "sign_classifier.pkl")

# =========================
# FEATURE EXTRACTION (CRITICAL)
# =========================
def extract_features(sample):
    """
    Convert 63 raw values → improved feature vector
    """

    coords = sample.values.reshape(21, 3)

    # ✅ 1. Normalize (same as prediction)
    wrist = coords[0]
    coords = coords - wrist

    coords[:, 2] *= 0.5

    max_val = np.max(np.abs(coords))
    if max_val != 0:
        coords = coords / max_val

    # ✅ Base features (63)
    features = coords.flatten().tolist()

    # =========================
    # ✅ IMPORTANT HAND FEATURES
    # =========================

    # Key fingertip indices
    index_tip = coords[8]
    middle_tip = coords[12]
    ring_tip = coords[16]
    pinky_tip = coords[20]

    # ✅ 2. Finger heights (critical for H)
    features.append(index_tip[1])
    features.append(middle_tip[1])
    features.append(ring_tip[1])
    features.append(pinky_tip[1])

    # ✅ 3. Finger separation (H vs B)
    features.append(abs(index_tip[1] - ring_tip[1]))
    features.append(abs(middle_tip[1] - pinky_tip[1]))

    # ✅ 4. Finger spread (H vs V/U)
    features.append(np.linalg.norm(index_tip - middle_tip))
    features.append(np.linalg.norm(middle_tip - ring_tip))

    # ✅ 5. Distance to wrist (folded vs extended)
    features.append(np.linalg.norm(index_tip))
    features.append(np.linalg.norm(middle_tip))
    features.append(np.linalg.norm(ring_tip))
    features.append(np.linalg.norm(pinky_tip))

    return features


# =========================
# LOAD DATASET
# =========================
print("📥 Loading dataset...")

df = pd.read_csv(CSV_PATH)

print("Dataset size:", len(df))

# ✅ IMPORTANT: shuffle dataset
df = df.sample(frac=1).reset_index(drop=True)

# =========================
# SPLIT FEATURES + LABELS
# =========================
X_raw = df.drop("label", axis=1)
y = df["label"]

# =========================
# APPLY FEATURE EXTRACTION
# =========================
print("⚙️ Extracting features...")

X = X_raw.apply(extract_features, axis=1, result_type='expand')

# =========================
# TRAIN / TEST SPLIT
# =========================
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42,
    stratify=y   # ✅ keeps balance
)

# =========================
# TRAIN MODEL (IMPROVED)
# =========================
print("\n🚀 Training model...")

model = RandomForestClassifier(
    n_estimators=400,
    max_depth=25,
    random_state=42
)

model.fit(X_train, y_train)

# =========================
# TEST ACCURACY
# =========================
print("\n📊 Evaluating model...")

y_pred = model.predict(X_test)

accuracy = accuracy_score(y_test, y_pred)

print(f"\n✅ Accuracy: {accuracy * 100:.2f}%")

# =========================
# SAVE MODEL
# =========================
with open(MODEL_PATH, "wb") as f:
    pickle.dump(model, f)

print("\n💾 Model saved successfully!")
print("Location:", MODEL_PATH)
