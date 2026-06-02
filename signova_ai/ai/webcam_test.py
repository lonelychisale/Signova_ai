import cv2
import mediapipe as mp
import os
import urllib.request
import numpy as np
import time
import requests
import json

from predict import predict_sign

# =========================
# API CONFIG
# =========================
API_URL = "http://127.0.0.1:8000/api/auth/predict-sign/"

# =========================
# PATH SETUP
# =========================
BASE_DIR = os.path.dirname(__file__)

MODEL_DIR = os.path.join(BASE_DIR, "models")
os.makedirs(MODEL_DIR, exist_ok=True)

MODEL_PATH = os.path.join(MODEL_DIR, "hand_landmarker.task")

MODEL_URL = (
    "https://storage.googleapis.com/"
    "mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/1/hand_landmarker.task"
)

# =========================
# DOWNLOAD MODEL
# =========================
if not os.path.exists(MODEL_PATH):
    print("⬇️ Downloading model...")
    urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
    print("✅ Model ready!")

# =========================
# MEDIAPIPE SETUP
# =========================
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.core.base_options import BaseOptions

base_options = BaseOptions(model_asset_path=MODEL_PATH)

options = vision.HandLandmarkerOptions(
    base_options=base_options,
    num_hands=1
)

landmarker = vision.HandLandmarker.create_from_options(options)

# =========================
# NORMALIZATION
# =========================
def normalize_sample(coords_list):
    coords = np.array(coords_list).reshape(21, 3)

    wrist = coords[0]
    coords = coords - wrist

    coords[:, 2] *= 0.5

    max_val = np.max(np.abs(coords))
    if max_val != 0:
        coords = coords / max_val

    return coords.flatten().tolist()

# =========================
# SENTENCE VARIABLES
# =========================
sentence = ""
current_prediction = ""
stable_prediction = ""
prediction_start_time = None
last_added_letter = ""

STABLE_TIME = 1.2
NO_HAND_TIMEOUT = 2.0

last_hand_seen = time.time()

# =========================
# CAMERA
# =========================
cap = cv2.VideoCapture(0)

print("\n🚀 System running (API + FULL COORDINATES + SENTENCE)")

# =========================
# LOOP
# =========================
while True:

    ret, frame = cap.read()
    if not ret:
        continue

    frame = cv2.flip(frame, 1)

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    mp_image = mp.Image(
        image_format=mp.ImageFormat.SRGB,
        data=rgb
    )

    result = landmarker.detect(mp_image)

    prediction = ""
    current_time = time.time()

    # =========================
    # HAND DETECTED
    # =========================
    if result.hand_landmarks:

        last_hand_seen = current_time

        for hand_landmarks in result.hand_landmarks:

            coordinates = []

            h, w, _ = frame.shape

            for lm in hand_landmarks:
                coordinates.extend([lm.x, lm.y, lm.z])

                cx = int(lm.x * w)
                cy = int(lm.y * h)
                cv2.circle(frame, (cx, cy), 4, (0, 255, 0), -1)

            # ✅ VALIDATE LENGTH
            if len(coordinates) != 63:
                print("❌ Invalid length:", len(coordinates))
                continue

            # ✅ Normalize
            normalized_coords = normalize_sample(coordinates)

            # =========================
            # ✅ PRINT FULL API FORMAT
            # =========================
            print("\n========================")
            print("✅ Length:", len(normalized_coords))

            json_data = json.dumps({
                "coordinates": [round(v, 6) for v in normalized_coords]
            })

            print("\n✅ COPY THIS JSON TO API:")
            print(json_data)

            # =========================
            # ✅ SEND TO API
            # =========================
            try:
                response = requests.post(
                    API_URL,
                    json={"coordinates": normalized_coords}
                )

                if response.status_code == 200:
                    prediction = response.json().get("prediction", "")
                else:
                    prediction = "ERR"

            except Exception as e:
                print("❌ API error:", e)
                prediction = ""

            print("Prediction:", prediction)

            # =========================
            # ✅ SENTENCE STABILIZATION
            # =========================
            if prediction != current_prediction:
                current_prediction = prediction
                prediction_start_time = current_time
            else:
                if prediction_start_time:
                    elapsed = current_time - prediction_start_time

                    if elapsed >= STABLE_TIME:
                        stable_prediction = prediction

                        if stable_prediction != last_added_letter:
                            sentence += stable_prediction
                            last_added_letter = stable_prediction
                            prediction_start_time = current_time

            # =========================
            # DRAW HAND CONNECTIONS
            # =========================
            connections = [
                (0,1),(1,2),(2,3),(3,4),
                (0,5),(5,6),(6,7),(7,8),
                (5,9),(9,10),(10,11),(11,12),
                (9,13),(13,14),(14,15),(15,16),
                (13,17),(17,18),(18,19),(19,20),
                (0,17)
            ]

            for start, end in connections:
                x1 = int(hand_landmarks[start].x * w)
                y1 = int(hand_landmarks[start].y * h)
                x2 = int(hand_landmarks[end].x * w)
                y2 = int(hand_landmarks[end].y * h)
                cv2.line(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)

    # =========================
    # AUTO SPACE
    # =========================
    else:
        if current_time - last_hand_seen > NO_HAND_TIMEOUT:
            if len(sentence) > 0 and not sentence.endswith(" "):
                sentence += " "
                last_added_letter = ""
                last_hand_seen = current_time

    # =========================
    # DISPLAY
    # =========================
    cv2.putText(frame, f"Prediction: {prediction}",
                (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1,
                (0, 255, 0), 2)

    cv2.putText(frame, f"Sentence: {sentence}",
                (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 1,
                (255, 255, 255), 2)

    cv2.putText(frame, "Q=Quit | C=Clear",
                (20, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                (255, 255, 0), 2)

    cv2.imshow("Sign Language System", frame)

    # =========================
    # KEYS
    # =========================
    key = cv2.waitKey(1) & 0xFF

    if key == ord("q"):
        break
    elif key == ord("c"):
        sentence = ""
        last_added_letter = ""
    elif key == 8:
        sentence = sentence[:-1]

# =========================
# CLEANUP
# =========================
cap.release()
cv2.destroyAllWindows()
