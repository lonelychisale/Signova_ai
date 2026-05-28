import cv2
import mediapipe as mp
import csv
import os
import urllib.request

# =========================
# PATH SETUP (SAVE IN /ai/)
# =========================
BASE_DIR = os.path.dirname(__file__)   # this script's folder (ai/)
DATA_DIR = os.path.join(BASE_DIR, "data")

os.makedirs(DATA_DIR, exist_ok=True)

CSV_FILE = os.path.join(DATA_DIR, "data.csv")

# =========================
# MODEL SETUP
# =========================
MODEL_DIR = os.path.join(BASE_DIR, "models")
MODEL_PATH = os.path.join(MODEL_DIR, "hand_landmarker.task")

MODEL_URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"

if not os.path.exists(MODEL_PATH):
    print("⬇️ Downloading model...")
    os.makedirs(MODEL_DIR, exist_ok=True)
    urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
    print("✅ Model downloaded!")

# =========================
# CREATE CSV FILE
# =========================
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        header = []

        for i in range(21):
            header.extend([f"x{i}", f"y{i}", f"z{i}"])

        header.append("label")
        writer.writerow(header)

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
# CAMERA
# =========================
cap = cv2.VideoCapture(0)

print("\n✅ Dataset Collector Started\n")
print(f"Saving dataset to:\n{CSV_FILE}\n")

print("Press:")
print("A = Save sign A")
print("B = Save sign B")
print("C = Save sign C")
print("Q = Quit\n")

# =========================
# LOOP
# =========================
while True:

    success, frame = cap.read()
    if not success:
        continue

    frame = cv2.flip(frame, 1)

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    mp_image = mp.Image(
        image_format=mp.ImageFormat.SRGB,
        data=rgb
    )

    result = landmarker.detect(mp_image)

    coordinates = None

    if result.hand_landmarks:

        for hand_landmarks in result.hand_landmarks:

            coordinates = []
            h, w, _ = frame.shape

            # Collect + draw points
            for lm in hand_landmarks:
                coordinates.extend([lm.x, lm.y, lm.z])

                cx, cy = int(lm.x * w), int(lm.y * h)
                cv2.circle(frame, (cx, cy), 5, (0, 255, 0), -1)

            # Draw connections
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

    cv2.imshow("Dataset Collector", frame)

    key = cv2.waitKey(1) & 0xFF

    # =========================
    # SAVE DATA
    # =========================
    if coordinates:

        if key == ord("a"):
            with open(CSV_FILE, "a", newline="") as f:
                csv.writer(f).writerow(coordinates + ["A"])
            print(f"✅ Saved A → {CSV_FILE}")

        elif key == ord("b"):
            with open(CSV_FILE, "a", newline="") as f:
                csv.writer(f).writerow(coordinates + ["B"])
            print(f"✅ Saved B → {CSV_FILE}")

        elif key == ord("c"):
            with open(CSV_FILE, "a", newline="") as f:
                csv.writer(f).writerow(coordinates + ["C"])
            print(f"✅ Saved C → {CSV_FILE}")

    if key == ord("q"):
        break

# =========================
# CLEANUP
# =========================
cap.release()
cv2.destroyAllWindows()
