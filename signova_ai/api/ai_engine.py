import json
import os
from moviepy.editor import VideoFileClip


class SignAIEngine:
    def __init__(self, dataset_path="dataset.json"):
        self.dataset_path = dataset_path
        self.dataset = []
        self.load_dataset()

    # =========================
    # LOAD DATASET
    # =========================
    def load_dataset(self):
        """
        Reload dataset dynamically
        So newly added data works instantly
        """

        try:
            with open(self.dataset_path, "r", encoding="utf-8") as f:
                self.dataset = json.load(f)

            print(f"[INFO] Dataset loaded successfully")
            print(f"[INFO] Total items: {len(self.dataset)}")

        except Exception as e:
            print(f"[ERROR] Failed to load dataset: {e}")
            self.dataset = []

    # =========================
    # PREPROCESS TEXT
    # =========================
    def preprocess(self, text):
        """
        Normalize text
        """

        processed = text.strip().lower()

        print(f"[DEBUG] Input Text : {text}")
        print(f"[DEBUG] Processed  : {processed}")

        return processed

    # =========================
    # VIDEO CONVERTER
    # =========================
    def get_web_ready_video(self, video_name):
        """
        Convert videos into browser-compatible MP4
        """

        if not video_name:
            return "unknown.mp4"

        # Safety check
        if isinstance(video_name, list):
            video_name = video_name[0]

        print(f"[DEBUG] Processing video: {video_name}")

        name, ext = os.path.splitext(video_name)

        fixed_name = f"{name}_fixed.mp4"

        original_path = os.path.join("media", "Signs", video_name)
        fixed_path = os.path.join("media", "Signs", fixed_name)

        # Use already converted version
        if os.path.exists(fixed_path):
            print(f"[INFO] Using cached fixed video: {fixed_name}")
            return fixed_name

        # File missing
        if not os.path.exists(original_path):
            print(f"[ERROR] File not found: {original_path}")
            return "unknown.mp4"

        try:
            print(f"[INFO] Converting video...")

            clip = VideoFileClip(original_path)

            clip.write_videofile(
                fixed_path,
                codec="libx264",
                audio_codec="aac",
                fps=30,
                preset="medium",
                bitrate="1200k",
                audio_bitrate="128k",
                threads=2,
                verbose=False,
                logger=None,
            )

            clip.close()

            print(f"[SUCCESS] Video converted: {fixed_name}")

            return fixed_name

        except Exception as e:
            print(f"[ERROR] Video conversion failed: {e}")

            return video_name

    # =========================
    # MATCH PHRASE
    # =========================
    def match_phrase(self, text):
        """
        Match short exact phrases
        """

        print(f"[DEBUG] Trying phrase match")

        for item in self.dataset:

            dataset_text = item.get("text", "").strip().lower()
            dataset_type = item.get("type", "").strip().lower()

            if dataset_type == "phrase" and dataset_text == text:

                print(f"[SUCCESS] Phrase matched: {dataset_text}")

                video = self.get_web_ready_video(item.get("video"))

                return [video]

        print("[DEBUG] No phrase match")

        return None

    # =========================
    # MATCH WORDS
    # =========================
    def match_words(self, text):
        """
        Match long sentence word-by-word
        """

        print(f"[DEBUG] Starting word matching")

        words = text.split()

        result = []

        for word in words:

            print(f"[DEBUG] Searching word: {word}")

            found = False

            for item in self.dataset:

                dataset_text = item.get("text", "").strip().lower()
                dataset_type = item.get("type", "").strip().lower()

                if dataset_type == "word" and dataset_text == word:

                    print(f"[SUCCESS] Word matched: {word}")

                    video = self.get_web_ready_video(item.get("video"))

                    result.append(video)

                    found = True

                    break

            # Word not found
            if not found:

                print(f"[WARNING] No match found for: {word}")

                result.append("unknown.mp4")

        print(f"[DEBUG] Final videos: {result}")

        return result

    # =========================
    # MAIN CONVERTER
    # =========================
    def convert(self, text):
        """
        Main conversion function

        Logic:
        - 1 or 2 words → try phrase matching
        - Long sentence → split into many videos
        """

        print("\n============================")
        print(f"[START] Converting: {text}")
        print("============================")

        # Reload latest dataset
        self.load_dataset()

        # Clean input
        text = self.preprocess(text)

        # Count words
        words = text.split()

        # SHORT TEXT → Try phrase matching first
        if len(words) <= 2:

            phrase_result = self.match_phrase(text)

            if phrase_result:
                return phrase_result

        # LONG TEXT → Word matching
        print("[INFO] Using word-by-word matching")

        return self.match_words(text)