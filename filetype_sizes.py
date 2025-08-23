'''
Analyzes the filetypes in a given directory and report their total sizes and counts. Create symlinks for files of a specific extension on the desktop. First, it recursively scans all files in the target folder, categorises them by extension, calculates the total size and number of files per type, and prints a sorted summary.

Quickly review and access large numbers of specific file types in mixed locations without touching the originals.
'''

import os
from collections import defaultdict
from pathlib import Path

def get_filetype_stats(base_path):
    filetype_sizes = defaultdict(int)
    filetype_counts = defaultdict(int)

    for root, _, files in os.walk(base_path):
        for file in files:
            file_path = os.path.join(root, file)
            if os.path.isfile(file_path):
                _, ext = os.path.splitext(file)
                ext = ext.lower() if ext else 'NO_EXTENSION'
                filetype_sizes[ext] += os.path.getsize(file_path)
                filetype_counts[ext] += 1

    return filetype_sizes, filetype_counts

def bytes_to_gb(bytes_size):
    return bytes_size / (1024 ** 3)

def create_symlinks_for_extension(source_dir, extension):
    extension = extension.lower()
    
    # Get desktop path and create preview folder
    desktop_path = Path.home() / "Desktop"
    symlink_dir = desktop_path / f"{extension[1:].upper()} previews"
    symlink_dir.mkdir(parents=True, exist_ok=True)

    count = 0

    for root, _, files in os.walk(source_dir):
        for file in files:
            if file.lower().endswith(extension):
                original_path = os.path.join(root, file)
                # Add count to filename to avoid collisions
                link_name = symlink_dir / f"{count}_{file}"

                try:
                    os.symlink(original_path, link_name)
                    count += 1
                except FileExistsError:
                    pass
                except OSError as e:
                    print(f"Error creating symlink for {original_path}: {e}")

    print(f"\nCreated {count} symlinks in: {symlink_dir}")

if __name__ == "__main__":
    source_directory = "/Volumes/My Passport for Mac/2024"

    # 1. Print filetype breakdown
    filetype_sizes, filetype_counts = get_filetype_stats(source_directory)
    sorted_types = sorted(filetype_sizes.items(), key=lambda x: x[1], reverse=True)

    print(f"{'Extension':>12} | {'Files':>8} | {'Total Size (GB)':>15}")
    print("-" * 40)
    for ext, size in sorted_types:
        count = filetype_counts[ext]
        print(f"{ext:>12} | {count:>8} | {bytes_to_gb(size):>15.2f}")

    if sorted_types:
        top_ext, top_size = sorted_types[0]
        print(f"\nLargest filetype: {top_ext} ({filetype_counts[top_ext]} files) using {bytes_to_gb(top_size):.2f} GB")
    else:
        print("No files found.")

    # 2. Create symlinks to .dng files on desktop
    create_symlinks_for_extension(source_directory, ".tif")