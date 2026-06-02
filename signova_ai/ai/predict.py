import os
import pickle
import numpy as np

# =========================
# LOAD MODEL
# =========================
BASE_DIR = os.path.dirname(__file__)

MODEL_PATH = os.path.join(BASE_DIR, "sign_classifier.pkl")

with open(MODEL_PATH, "rb") as f:
    model = pickle.load(f)


# =========================
# FEATURE EXTRACTION (SAME AS TRAINING)
# =========================
def extract_features(coordinates):

    coords = np.array(coordinates).reshape(21, 3)

    # Normalize
    wrist = coords[0]
    coords = coords - wrist

    coords[:, 2] *= 0.5

    max_val = np.max(np.abs(coords))
    if max_val != 0:
        coords = coords / max_val

    features = coords.flatten().tolist()

    # Key fingertips
    index_tip = coords[8]
    middle_tip = coords[12]
    ring_tip = coords[16]
    pinky_tip = coords[20]

    # Finger heights
    features.append(index_tip[1])
    features.append(middle_tip[1])
    features.append(ring_tip[1])
    features.append(pinky_tip[1])

    # Differences
    features.append(abs(index_tip[1] - ring_tip[1]))
    features.append(abs(middle_tip[1] - pinky_tip[1]))

    # Distances
    features.append(np.linalg.norm(index_tip - middle_tip))
    features.append(np.linalg.norm(middle_tip - ring_tip))

    features.append(np.linalg.norm(index_tip))
    features.append(np.linalg.norm(middle_tip))
    features.append(np.linalg.norm(ring_tip))
    features.append(np.linalg.norm(pinky_tip))

    return features


# =========================
# PREDICT FUNCTION
# =========================
def predict_sign(coordinates):

    features = extract_features(coordinates)

    prediction = model.predict([features])[0]

    return prediction
