import subprocess
import sys

OUTPUT = "output-collage.mp4"


def combine_three(v1, v2, v3, output=OUTPUT):
    """
    Combines three 640x1080 videos into one 1920x1080 video.
    Layout:
    [ video1 | video2 | video3 ]
    """

    cmd = [
        "ffmpeg",
        "-y",

        "-i", v1,
        "-i", v2,
        "-i", v3,

        # build 1920x1080 canvas and place videos
        "-filter_complex",
        (
            "nullsrc=size=1920x1080 [base];"
            "[0:v] setpts=PTS-STARTPTS [left];"
            "[1:v] setpts=PTS-STARTPTS [mid];"
            "[2:v] setpts=PTS-STARTPTS [right];"

            "[base][left] overlay=shortest=1:x=0:y=0 [tmp1];"
            "[tmp1][mid] overlay=shortest=1:x=640:y=0 [tmp2];"
            "[tmp2][right] overlay=shortest=1:x=1280:y=0"
        ),

        "-c:v", "libx264",
        "-crf", "18",
        "-preset", "medium",
        "-pix_fmt", "yuv420p",
        output
    ]

    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python triple_stack.py video1.mp4 video2.mp4 video3.mp4")
        sys.exit(1)

    combine_three(sys.argv[1], sys.argv[2], sys.argv[3])
