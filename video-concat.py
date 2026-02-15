import os
import json
import random
import subprocess
import tempfile
import sys
from concurrent.futures import ThreadPoolExecutor

# ===== CONFIG =====
CONFIG_FILE = "video-concat.config"
OUTPUT_FILE = "output4.mp4"
TARGET_WIDTH = 640
TARGET_HEIGHT = 1080
MAX_WORKERS = 4  # adjust to CPU/GPU capability
# ==================


def load_config():
    if not os.path.exists(CONFIG_FILE):
        sys.exit(f"Config file not found: {CONFIG_FILE}")

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)

    return config["audio_source"], config["directories"]


def collect_videos(directories):
    videos = []
    for directory in directories:
        print(f"Scanning {directory}")
        for root, _, files in os.walk(directory):
            for f in files:
                if f.lower().endswith(".mp4"):
                    videos.append(os.path.join(root, f))
    return videos


# ---------- GPU NORMALIZATION ----------
def normalize_video(input_path, output_path):
    """
    Scale proportionally → crop center → GPU encode.
    Produces identical resolution + codec for safe concat.
    """

    vf = (
        f"scale={TARGET_WIDTH}:{TARGET_HEIGHT}:"
        "force_original_aspect_ratio=increase,"
        f"crop={TARGET_WIDTH}:{TARGET_HEIGHT},"
        "setsar=1"
    )

    cmd = [
        "ffmpeg",
        "-y",
        "-hwaccel", "auto",          # GPU decode if available
        "-i", input_path,
        "-vf", vf,

        # GPU encode (fast)
        "-c:v", "h264_nvenc",
        "-preset", "p4",             # speed/quality balance (p1 fastest, p7 best)
        "-cq", "23",

        # ensure concat compatibility
        "-pix_fmt", "yuv420p",
        "-r", "30",
        "-an",                       # drop audio (we use external audio later)

        output_path
    ]

    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)


def normalize_all(videos, temp_dir):
    print("Normalizing videos (GPU + parallel)...")

    normalized = []

    def process(i, v):
        out = os.path.join(temp_dir, f"norm_{i}.mp4")
        normalize_video(v, out)
        return out

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = [ex.submit(process, i, v) for i, v in enumerate(videos)]
        for f in futures:
            normalized.append(f.result())

    return normalized


# ---------- CONCAT ----------
def concat_videos(videos, audio_source):
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        concat_file = f.name
        for v in videos:
            f.write(f"file '{v}'\n")

    cmd = [
        "ffmpeg",
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_file,
        "-i", audio_source,
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-af", "apad",
        "-shortest",

        # final encode (can also use nvenc)
        # "-c:v", "h264_nvenc",
        # "-preset", "p5",
        # "-cq", "21",

        # -c:v copy
        # But only safe if all normalized files match perfectly (this script already ensures that).
        "-c:v", "copy",

        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        OUTPUT_FILE
    ]

    subprocess.run(cmd, check=True)
    os.remove(concat_file)


# ---------- MAIN ----------
def main():
    audio_source, directories = load_config()

    videos = collect_videos(directories)
    if not videos:
        raise RuntimeError("No videos found.")

    random.shuffle(videos)
    print(f"Video count: {len(videos)}")

    with tempfile.TemporaryDirectory() as temp_dir:
        normalized = normalize_all(videos, temp_dir)
        concat_videos(normalized, audio_source)

    print(f"\nDone → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
