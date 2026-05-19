from moviepy import VideoFileClip

# Load your downloaded YouTube file
clip = VideoFileClip("Signs/help.mp4")

# Write it back using the universal web codec: libx264
clip.write_videofile(
    "Signs/help_fixed.mp4", 
    codec="libx264", 
    audio_codec="aac"
)
