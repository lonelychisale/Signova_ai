import json
import os

class SignAIEngine:
    def __init__(self, dataset_path="dataset.json"):
        with open(dataset_path, "r") as f:
            self.dataset = json.load(f)

    def preprocess(self, text):
        return text.lower().strip()

    def get_web_ready_video(self, video_name):
        """
        Helper function: If a fixed version exists in the Signs folder, 
        use it to fix browser playback issues automatically.
        """
        if not video_name:
            return "unknown.mp4"
            
        # Split 'help.mp4' into 'help' and '.mp4'
        name, ext = os.path.splitext(video_name)
        fixed_name = f"{name}_fixed{ext}" # help_fixed.mp4
        
        # Check if the fixed file physically exists in your Signs folder
        if os.path.exists(os.path.join("Signs", fixed_name)):
            return fixed_name
        return video_name

    def match_phrase(self, text):
        for item in self.dataset:
            if item["type"] == "phrase" and item["text"] == text:
                # Wrap the output in a list to match match_words format
                video = self.get_web_ready_video(item["video"])
                return [video] 
        return None

    def match_words(self, text):
        words = text.split()
        result = []
        for word in words:
            found = False
            for item in self.dataset:
                if item["type"] == "word" and item["text"] == word:
                    video = self.get_web_ready_video(item["video"])
                    result.append(video)
                    found = True
                    break
            if not found:
                result.append("unknown.mp4")
        return result

    def convert(self, text):
        text = self.preprocess(text)
        phrase = self.match_phrase(text)
        if phrase:
            return phrase
        return self.match_words(text)
