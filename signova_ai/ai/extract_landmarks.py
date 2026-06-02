import cv2
import mediapipe as mp
import csv
import os
import urllib.request
import numpy as np

# =========================
# PATHS
# =========================
BASE_DIR = os.path.dirname(__file__)

DATASET_DIR = os.path.join(BASE_DIR, "asl_dataset")

DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

CSV_FILE = os.path.join(DATA_DIR, "data.csv")

# =========================
# MODEL SETUP
# =========================
MODEL_DIR = os.path.join(BASE_DIR, "models")
MODEL_PATH = os.path.join(MODEL_DIR, "hand_landmarker.task")

MODEL_URL = (
    "https://storage.googleapis.com/"
    "mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/1/"
    "hand_landmarker.task"
)

# =========================
# DOWNLOAD MODEL (if missing)
# =========================
if not os.path.exists(MODEL_PATH):

    print("⬇️ Downloading MediaPipe model...")

    os.makedirs(MODEL_DIR, exist_ok=True)

    urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)

    print("✅ Model downloaded!")

# =========================
# CSV HEADER
# =========================
headers = []

for i in range(21):
    headers.extend([f"x{i}", f"y{i}", f"z{i}"])

headers.append("label")

# =========================
# CREATE CSV FILE
# =========================
with open(CSV_FILE, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(headers)

# =========================
# MEDIAPIPE TASKS API
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

landmarker = vision.HandLandmarker.create_from_options(options)

# =========================
# PROCESS DATASET
# =========================
print("\n🚀 Processing dataset...\n")

total_saved = 0
skipped = 0

# ✅ Open CSV ONCE (fast)
with open(CSV_FILE, "a", newline="") as f:
    writer = csv.writer(f)

    # Loop through labels (A, B, C...)
    for label in os.listdir(DATASET_DIR):

        label_path = os.path.join(DATASET_DIR, label)

        if not os.path.isdir(label_path):
            continue

        print(f"📂 Processing letter: {label}")

        # Loop through images
        for image_name in os.listdir(label_path):

            image_path = os.path.join(label_path, image_name)

            image = cv2.imread(image_path)

            if image is None:
                skipped += 1
                continue

            rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            mp_image = mp.Image(
                image_format=mp.ImageFormat.SRGB,
                data=rgb
            )

            result = landmarker.detect(mp_image)

            # =========================
            # HAND FOUND
            # =========================
            if not result.hand_landmarks:
                skipped += 1
                continue

            for hand_landmarks in result.hand_landmarks:

                # =========================
                # EXTRACT COORDINATES
                # =========================
                coords = []

                for lm in hand_landmarks:
                    coords.append([lm.x, lm.y, lm.z])

                coords = np.array(coords)

                # =========================
                # NORMALIZATION (CRITICAL)
                # =========================

                # ✔ 1. Center (wrist)
                wrist = coords[0]
                coords = coords - wrist

                # ✔ 2. Reduce Z effect
                coords[:, 2] *= 0.5

                # ✔ 3. Scale normalization
                max_val = np.max(np.abs(coords))
                if max_val != 0:
                    coords = coords / max_val

                # Flatten
                row = coords.flatten().tolist()

                # Add label
                row.append(label)

                # Save to CSV
                writer.writerow(row)

                total_saved += 1

# =========================
# DONE
# =========================
print("\n✅ DATASET COMPLETE!")
print(f"✅ Saved samples: {total_saved}")
print(f"⚠️ Skipped images: {skipped}")
print(f"📁 CSV location: {CSV_FILE}")