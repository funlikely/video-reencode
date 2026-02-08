# python script that does the following
#
# contains a hardcoded list of directory paths that I'll modify manually
#
# makes a single randomly ordered list of all the .mp4 files in those directories
#
# concatenates all those mp4s using ffmpeg into a single mp4.  I want the output video to be 1504x832 which is most of the source videos. skip videos that aren't that size.
#
# use the audio track from an audio source mp4, 'audio-source.mp4'.
#
# end the output mp4 once all the source videos are used.  the audio source will be too short, so the rest of the output video should be silent.

import os
import json
import random
import subprocess
import tempfile
import sys

# ===== CONFIG =====
CONFIG_FILE = "video-concat.config"
OUTPUT_FILE = "output3.mp4"
TARGET_WIDTH = 1504
TARGET_HEIGHT = 832
# TARGET_WIDTH = 928
# TARGET_HEIGHT = 1376
# ==================


def load_config():
    if not os.path.exists(CONFIG_FILE):
        sys.exit(f"Config file not found: {CONFIG_FILE}")

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)

    try:
        audio_source = config["audio_source"]
        directories = config["directories"]
    except KeyError as e:
        sys.exit(f"Missing required config key: {e}")

    if not isinstance(directories, list):
        sys.exit("directories must be a list")

    return audio_source, directories


def get_video_resolution(path):
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "csv=p=0",
        path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return None
    try:
        w, h = map(int, result.stdout.strip().split(","))
        return w, h
    except ValueError:
        return None


def collect_videos(directories):
    videos = []
    for directory in directories:
        for root, _, files in os.walk(directory):
            for f in files:
                if f.lower().endswith(".mp4"):
                    full_path = os.path.join(root, f)
                    res = get_video_resolution(full_path)
                    if res == (TARGET_WIDTH, TARGET_HEIGHT):
                        videos.append(full_path)
    return videos


def main():

    audio_source, directories = load_config()

    videos = collect_videos(directories)
    if not videos:
        raise RuntimeError("No matching videos found.")

    random.shuffle(videos)

    # Create concat file
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        concat_file = f.name
        for v in videos:
            escaped = v.replace("'", "'\\''")
            f.write(f"file '{escaped}'\n")

    # ffmpeg command
    cmd = [
        "ffmpeg",
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_file,
        "-i", audio_source,
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-vf", f"scale={TARGET_WIDTH}:{TARGET_HEIGHT}",
        "-af", "apad",
        "-shortest",
        "-c:v", "libx264",
        "-preset", "slow",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-profile:v", "high",
        "-level", "4.1",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        OUTPUT_FILE
    ]

    subprocess.run(cmd, check=True)
    os.remove(concat_file)

    print(f"Done. Output written to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()


