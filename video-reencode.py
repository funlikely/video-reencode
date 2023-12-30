import os
import subprocess
import psutil
import argparse
import configparser


def read_config(file_path='H:\\streaming-dvr\\config.ini'):
    config = configparser.ConfigParser()
    config.read(file_path)
    return config


def run_ffmpeg_with_cpu_affinity_and_priority(ffmpeg_command, cpu_affinity):
    # Read configuration from the file each time we start a new ffmpeg command
    affinity_list = get_affinity_list()
    print(f'Affinity list: {affinity_list}')

    ffmpeg_process = subprocess.Popen(ffmpeg_command)

    # Get the PID of the ffmpeg process
    pid = ffmpeg_process.pid

    # Set CPU affinity using psutil
    process = psutil.Process(pid)
    process.cpu_affinity(affinity_list)

    # Set process priority to below normal
    process.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)

    # Wait for the ffmpeg process to complete
    ffmpeg_process.communicate()


def get_affinity_list():
    # Get affinity and priority from the configuration with a default value
    try:
        config = read_config()
        affinity_value_str = config.get('ffmpeg', 'affinity')
        affinity_list = [int(core.strip()) for core in affinity_value_str.split(',')]
    except ValueError:
        # Parsing error, set a default value
        affinity_list = [0]

    return affinity_list


def convert_ts_to_mp4(input_folder, output_folder):
    # Make sure the output folder exists
    os.makedirs(output_folder, exist_ok=True)

    # Get a list of all .ts files in the input folder
    ts_files = [f for f in os.listdir(input_folder) if f.endswith('.ts')]

    for ts_file in ts_files:
        input_path = os.path.join(input_folder, ts_file)
        output_path = os.path.join(output_folder, os.path.splitext(ts_file)[0] + '.mp4')
        print(f'Start converting {input_path} to {output_path}')

        # Run ffmpeg command to reencode .ts to .mp4 with lower bitrate
        command = ['ffmpeg', '-i', input_path, '-c:v', 'libx264', '-crf', '23', '-c:a', 'aac', '-strict',
                   'experimental', output_path]
        cpu_affinity = [2, 3, 4, 5, 6]  # List of CPU core indices
        run_ffmpeg_with_cpu_affinity_and_priority(command, cpu_affinity)
        print(f'Finished converting {input_path} to {output_path}')


def convert_iso_to_mp4(iso_path, output_path):
    # Run FFmpeg command to convert ISO to MP4
    command = [
        'ffmpeg',
        '-i', iso_path,
        '-map', '0:0', '-c:v', 'libx264', '-c:a', 'pcm_s16le',
        output_path
    ]
    subprocess.run(command)


def parse_arguments():
    parser = argparse.ArgumentParser(description='Convert ISO to MP4 using FFmpeg.')
    parser.add_argument('--isolocation', help='Path to the input ISO file', required=False)
    parser.add_argument('--outputlocation', help='Path to the output MP4 file', required=False)
    return parser.parse_args()


if __name__ == "__main__":
    # Parse command-line arguments
    args = parse_arguments()

    if not (args.isolocation or args.outputlocation):
        convert_ts_to_mp4('H:\\streaming-dvr\\source', 'H:\\streaming-dvr\\destination')

    # Check if the input ISO file exists
    if not os.path.exists(args.isolocation):
        print(f"Error: Input ISO file '{args.isolocation}' not found.")
    else:
        # Convert ISO to MP4
        convert_iso_to_mp4(args.isolocation, args.outputlocation)
        print(f"Conversion complete. Output saved to '{args.outputlocation}'.")
