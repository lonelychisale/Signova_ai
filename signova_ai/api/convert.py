# # from moviepy import VideoFileClip

# # # Load your downloaded YouTube file
# # clip = VideoFileClip("Signs/help.mp4")

# # # Write it back using the universal web codec: libx264
# # clip.write_videofile(
# #     "Signs/help_fixed.mp4", 
# #     codec="libx264", 
# #     audio_codec="aac"
# # )
# from moviepy import VideoFileClip
# import os

# # def convert_to_mp4(input_path):
# #     name, ext = os.path.splitext(input_path)
# #     output_path = f"{name}_fixed.mp4"

# #     # ✅ Skip if already converted
# #     if os.path.exists(output_path):
# #         print(f"[INFO] Already converted: {output_path}")
# #         return output_path

# #     print(f"[INFO] Converting {input_path} → {output_path}")

# #     clip = VideoFileClip(input_path)
# #     clip.write_videofile(
# #         output_path,
# #         codec="libx264",
# #         audio_codec="aac"
# #     )

# #     return output_path
