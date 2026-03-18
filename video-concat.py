import os
import json
import random
import subprocess
import tempfile
import sys
from concurrent.futures import ThreadPoolExecutor

# ===== CONFIG =====
CONFIG_FILE = "video-concat.config"
# ==================


def load_config():
    if not os.path.exists(CONFIG_FILE):
        sys.exit(f"Config file not found: {CONFIG_FILE}")

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)

    return config["concatenated_videos"]


def get_speed(video_path):
    # your logic here
    return random.choice([0.95, 0.90, 1.00, 0.85])


def mirror_video(video_path):
    # your logic here
    return random.choice([True, False])


def run_job(config):
    print(f"\n=== Processing: {config['output_file']} ===")

    videos = collect_videos(config["directories"])
    if not videos:
        print("No videos found, skipping.")
        return

    random.shuffle(videos)
    print(f"Video count: {len(videos)}")

    with tempfile.TemporaryDirectory() as temp_dir:
        normalized = normalize_all(
            videos,
            temp_dir,
            config["target_width"],
            config["target_height"],
            config["max_workers"],
            config.get("keep_audio", False)
        )

        concat_videos(
            normalized,
            config["audio_source"],
            config["output_file"],
            config.get("keep_audio", False)
        )

    print(f"Done → {config['output_file']}")


def collect_videos(directories):
    videos = []
    for directory in directories:
        print(f"Scanning {directory}")
        for root, _, files in os.walk(directory):
            for f in files:
                if f.lower().endswith(".mp4"):
                    videos.append(os.path.join(root, f))
    return videos


def build_atempo_filter(speed):
    filters = []
    while speed > 2.0:
        filters.append("atempo=2.0")
        speed /= 2.0
    while speed < 0.5:
        filters.append("atempo=0.5")
        speed *= 2.0
    filters.append(f"atempo={speed}")
    return ",".join(filters)


# ---------- GPU NORMALIZATION ----------
def normalize_video(input_path, output_path, target_width, target_height, keep_audio):
    """
    Scale proportionally → crop center → GPU encode.
    Produces identical resolution + codec for safe concat.
    """
    speed = get_speed(input_path)
    mirror = mirror_video(input_path)

    vf_parts = [
        f"scale={target_width}:{target_height}:force_original_aspect_ratio=increase",
        f"crop={target_width}:{target_height}",
        "setsar=1",
        f"setpts={1 / speed}*PTS"
    ]

    if mirror:
        vf_parts.append("hflip")

    vf = ",".join(vf_parts)

    cmd = [
        "ffmpeg",
        "-y",
        "-hwaccel", "auto",
        "-i", input_path,
        "-vf", vf,

        "-c:v", "h264_nvenc",
        "-preset", "p4",
        "-cq", "23",

        "-pix_fmt", "yuv420p",
        "-r", "30",
    ]

    if keep_audio:
        atempo_filter = build_atempo_filter(speed)
        cmd += [
            "-af", atempo_filter,
            "-c:a", "aac",
            "-b:a", "128k",
        ]
    else:
        cmd += ["-an"]

    cmd.append(output_path)


    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)


def normalize_all(videos, temp_dir, target_width, target_height, max_workers, keep_audio):
    print("Normalizing videos (GPU + parallel)...")

    normalized = []

    def process(i, v):
        out = os.path.join(temp_dir, f"norm_{i}.mp4")
        normalize_video(v, out, target_width, target_height, keep_audio)
        return out

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = [ex.submit(process, i, v) for i, v in enumerate(videos)]
        for f in futures:
            normalized.append(f.result())

    return normalized


# ---------- CONCAT ----------
def concat_videos(videos, audio_source, output_file, keep_audio):
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        concat_file = f.name
        for v in videos:
            f.write(f"file '{v}'\n")

    if keep_audio:
        cmd = [
            "ffmpeg",
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_file,

            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            output_file
        ]
    else:
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

            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            output_file
        ]

    subprocess.run(cmd, check=True)
    os.remove(concat_file)


# ---------- MAIN ----------
def main():
    configs = load_config()

    for config in configs:
        try:
            run_job(config)
        except Exception as e:
            print(f"❌ Failed: {config.get('output_file')} → {e}")


if __name__ == "__main__":
    main()
