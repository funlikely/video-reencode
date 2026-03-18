import subprocess
import sys
import json


def combine_three(video_configs, output):
    if len(video_configs) != 3:
        raise ValueError("Exactly 3 videos are required.")

    cmd = ["ffmpeg", "-y"]

    audio_inputs = []
    filter_parts = []

    # Add inputs
    for i, v in enumerate(video_configs):
        cmd.extend(["-i", v["path"]])

        # Track audio inputs
        if v.get("keep_audio", False):
            audio_inputs.append(f"[{i}:a]")

    # Video layout
    filter_parts.append("nullsrc=size=1920x1080 [base];")
    filter_parts.append("[0:v] setpts=PTS-STARTPTS [left];")
    filter_parts.append("[1:v] setpts=PTS-STARTPTS [mid];")
    filter_parts.append("[2:v] setpts=PTS-STARTPTS [right];")

    filter_parts.append("[base][left] overlay=shortest=1:x=0:y=0 [tmp1];")
    filter_parts.append("[tmp1][mid] overlay=shortest=1:x=640:y=0 [tmp2];")
    filter_parts.append("[tmp2][right] overlay=shortest=1:x=1280:y=0 [vout];")

    # Audio handling
    if len(audio_inputs) > 1:
        # Mix multiple audio streams
        inputs_str = "".join(audio_inputs)
        filter_parts.append(
            f"{inputs_str} amix=inputs={len(audio_inputs)}:duration=shortest [aout];"
        )
    elif len(audio_inputs) == 1:
        # Single audio stream (no mix needed)
        filter_parts.append(f"{audio_inputs[0]} anull [aout];")

    filter_complex = "".join(filter_parts).rstrip(";")

    cmd.extend([
        "-filter_complex", filter_complex,
        "-map", "[vout]"
    ])

    if audio_inputs:
        cmd.extend(["-map", "[aout]"])
    else:
        cmd.append("-an")  # no audio

    cmd.extend([
        "-c:v", "libx264",
        "-crf", "18",
        "-preset", "medium",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        output
    ])

    print("FFMPEG CMD:\n", " ".join(cmd))
    subprocess.run(cmd, check=True)


def load_config(path):
    with open(path, "r") as f:
        return json.load(f)


if __name__ == "__main__":

    config = load_config("video-collage.config")

    videos = config.get("videos")
    output = config.get("output", "output-collage.mp4")

    if not videos:
        raise ValueError("Config must include 'videos' list.")

    combine_three(videos, output)