'''
Search for files with specified filetype in a specified directory, calculate the total size, list their file paths, and copy to new folder if "download" argument is included
'''

import os
import shutil
import sys

def list_video_files(directory):
    video_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(('.360')):
                video_files.append(os.path.join(root, file))
    return video_files

def bytes_to_gb(size_in_bytes):
    return size_in_bytes / (1024**3)

def copy_to_videos_directory(video_files):
    # desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
    # videos_dir = os.path.join(desktop_path, 'Seoul Videos')
    videos_dir = ""
    os.makedirs(videos_dir, exist_ok=True)
    
    total_files = len(video_files)
    copied_files = 0

    print("Copying files:")
    for file in video_files:
        shutil.copy(file, videos_dir)
        copied_files += 1

        # Calculate progress percentage
        progress_percentage = (copied_files / total_files) * 100
        print(f"\rProgress: {copied_files}/{total_files} files ({progress_percentage:.2f}%)", end="", flush=True)

    print("\nVideo files copied to ", videos_dir)

def main():
    #directory = "/Volumes/One Touch/2023/Asia 23"
    #directory = "/Volumes/One Touch/2022/Seoul"
    directory = "/Volumes/5TB Backup/China/Manulife Plaza"
    #directory = "/Volumes/One Touch/Edits"
    if not os.path.isdir(directory):
        print("Directory '{}' not found.".format(directory))
        return
    
    video_files = list_video_files(directory)
    if video_files:
        print("Video files in '{}' directory:".format(directory))
        total_size = 0
        num_files = 0  # Initialize the file count
        for file in video_files:
            file_size = os.path.getsize(file)
            total_size += file_size
            num_files += 1  # Increment the file count
            print(file)
        total_size_gb = bytes_to_gb(total_size)
        print("Total combined size of video files: {:.2f} GB".format(total_size_gb))
        print("Number of video files found:", num_files)  # Print the file count
        
        # Check if the "download" argument is provided
        if len(sys.argv) > 1 and sys.argv[1] == "download":
            copy_to_videos_directory(video_files)
    else:
        print("No video files found in '{}' directory.".format(directory))

if __name__ == "__main__":
    main()
