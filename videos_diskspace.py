'''
Total disk space used by video files in a folder
'''

import os

def get_total_videos_folder_size(base_path):
    total_size = 0
    videos_folders = []

    for root, dirs, files in os.walk(base_path):
        for d in dirs:
            if d == "Videos":
                videos_folder = os.path.join(root, d)
                videos_folders.append(videos_folder)

    for folder in videos_folders:
        for root, _, files in os.walk(folder):
            for file in files:
                file_path = os.path.join(root, file)
                if os.path.isfile(file_path):
                    total_size += os.path.getsize(file_path)

    return total_size

def bytes_to_gb(bytes_size):
    return bytes_size / (1024 ** 3)

if __name__ == "__main__":
    directory = "/Volumes/My Passport for Mac/2024"

    total_bytes = get_total_videos_folder_size(directory)
    print(f"Total size of all 'Videos' folders: {bytes_to_gb(total_bytes):.2f} GB")
