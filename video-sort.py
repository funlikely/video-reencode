import os
import shutil
import keyboard
import subprocess
import json

CONFIG_FILE = "video-sort.config"

with open(CONFIG_FILE, "r") as f:
    config = json.load(f)

SOURCE_FOLDER = config["source_folder"]
DESTINATIONS = config["destinations"]
SUPPORTED = tuple(config["supported_extensions"])
VLC_PATH = config["vlc_path"]


files = [
    f for f in os.listdir(SOURCE_FOLDER)
    if f.lower().endswith(SUPPORTED)
]

index = 0
current_process = None


def open_in_vlc(path):
    global current_process
    if current_process:
        current_process.terminate()

    current_process = subprocess.Popen(
        [VLC_PATH, "--play-and-exit", path],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

def load_next():
    if index < len(files):
        path = os.path.join(SOURCE_FOLDER, files[index])
        open_in_vlc(path)

def close_vlc():
    global current_process
    if current_process:
        current_process.terminate()
        try:
            current_process.wait(timeout=2)
        except:
            pass
        current_process = None


def move_current(key):
    global index

    if index >= len(files):
        return

    # close VLC first so file isn't locked
    close_vlc()

    src = os.path.join(SOURCE_FOLDER, files[index])
    dst = os.path.join(DESTINATIONS[key], files[index])

    # small delay helps Windows release file lock
    import time
    time.sleep(0.15)

    shutil.move(src, dst)
    print(f"Moved -> {dst}")

    index += 1
    load_next()

for key in DESTINATIONS.keys():
    keyboard.add_hotkey(key, lambda k=key: move_current(k))

print("Sorting ready. Press ESC to quit.")
load_next()
keyboard.wait("esc")