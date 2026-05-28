import cv2
import mediapipe as mp
import os
import urllib.request
import time

from predict import predict_sign

# =========================
# MODEL SETUP
# =========================
BASE_DIR = os.path.dirname(__file__)

MODEL_DIR = os.path.join(BASE_DIR, "models")

MODEL_PATH = os.path.join(
    MODEL_DIR,
    "hand_landmarker.task"
)

MODEL_URL = (
    "https://storage.googleapis.com/"
    "mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/1/"
    "hand_landmarker.task"
)

if not os.path.exists(MODEL_PATH):

    print("Downloading model...")

    os.makedirs(MODEL_DIR, exist_ok=True)

    urllib.request.urlretrieve(
        MODEL_URL,
        MODEL_PATH
    )

# =========================
# MEDIAPIPE
# =========================
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.core.base_options import BaseOptions

base_options = BaseOptions(
    model_asset_path=MODEL_PATH
)

options = vision.HandLandmarkerOptions(
    base_options=base_options,
    num_hands=1
)

landmarker = vision.HandLandmarker.create_from_options(
    options
)

# =========================
# CAMERA
# =========================
cap = cv2.VideoCapture(0)

# =========================
# TEXT VARIABLES
# =========================
current_letter = ""
last_letter = ""

sentence = ""

last_prediction_time = time.time()

PREDICTION_DELAY = 1.0

print("\n🚀 Sign Language Word Builder Started")
print("Press:")
print("SPACE = add space")
print("BACKSPACE = delete last letter")
print("C = clear sentence")
print("Q = quit\n")

# =========================
# LOOP
# =========================
while True:

    success, frame = cap.read()

    if not success:
        continue

    frame = cv2.flip(frame, 1)

    rgb = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2RGB
    )

    mp_image = mp.Image(
        image_format=mp.ImageFormat.SRGB,
        data=rgb
    )

    result = landmarker.detect(mp_image)

    prediction = ""

    if result.hand_landmarks:

        for hand_landmarks in result.hand_landmarks:

            coordinates = []

            h, w, _ = frame.shape

            # =========================
            # EXTRACT LANDMARKS
            # =========================
            for lm in hand_landmarks:

                coordinates.extend([
                    lm.x,
                    lm.y,
                    lm.z
                ])

                cx = int(lm.x * w)
                cy = int(lm.y * h)

                cv2.circle(
                    frame,
                    (cx, cy),
                    5,
                    (0, 255, 0),
                    -1
                )

            # =========================
            # PREDICT LETTER
            # =========================
            prediction = predict_sign(
                coordinates
            )

            # =========================
            # SMART LETTER ADDING
            # =========================
            current_time = time.time()

            if (
                prediction != last_letter
                and current_time - last_prediction_time > PREDICTION_DELAY
            ):

                sentence += prediction

                last_letter = prediction

                last_prediction_time = current_time

            # =========================
            # DRAW CONNECTIONS
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

                cv2.line(
                    frame,
                    (x1, y1),
                    (x2, y2),
                    (255, 0, 0),
                    2
                )

    # =========================
    # DISPLAY
    # =========================
    cv2.putText(
        frame,
        f"Current: {prediction}",
        (20, 50),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 255, 0),
        2
    )

    cv2.putText(
        frame,
        f"Text: {sentence}",
        (20, 100),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (255, 255, 255),
        2
    )

    cv2.imshow(
        "Sign Language Word Builder",
        frame
    )

    # =========================
    # KEYS
    # =========================
    key = cv2.waitKey(1) & 0xFF

    # Quit
    if key == ord("q"):
        break

    # Add space
    elif key == 32:
        sentence += " "

    # Clear
    elif key == ord("c"):
        sentence = ""

    # Backspace
    elif key == 8:
        sentence = sentence[:-1]

# =========================
# CLEANUP
# =========================
cap.release()
cv2.destroyAllWindows()