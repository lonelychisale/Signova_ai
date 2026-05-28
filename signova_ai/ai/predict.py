import os
import pickle
import numpy as np

# =========================
# LOAD MODEL
# =========================
BASE_DIR = os.path.dirname(__file__)

MODEL_PATH = os.path.join(
    BASE_DIR,
    "sign_classifier.pkl"
)

with open(MODEL_PATH, "rb") as f:
    model = pickle.load(f)

# =========================
# PREDICT FUNCTION
# =========================
def predict_sign(coordinates):

    prediction = model.predict(
        np.array(coordinates).reshape(1, -1)
    )

    return prediction[0]