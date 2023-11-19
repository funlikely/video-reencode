import os
import subprocess


def convert_ts_to_mp4(input_folder, output_folder):
    # Make sure the output folder exists
    os.makedirs(output_folder, exist_ok=True)

    # Get a list of all .ts files in the input folder
    ts_files = [f for f in os.listdir(input_folder) if f.endswith('.ts')]

    for ts_file in ts_files:
        input_path = os.path.join(input_folder, ts_file)
        output_path = os.path.join(output_folder, os.path.splitext(ts_file)[0] + '.mp4')

        # Run ffmpeg command to convert .ts to .mp4
        command = ['ffmpeg', '-i', input_path, '-c', 'copy', output_path]
        subprocess.run(command)


if __name__ == "__main__":
    # Specify your input and output folders
    input_folder = '/path/to/input/folder'
    output_folder = '/path/to/output/folder'

    # Call the function to convert .ts to .mp4
    convert_ts_to_mp4(input_folder, output_folder)
