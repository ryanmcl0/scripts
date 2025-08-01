'''
Copy all edited files within a specified directory to a new directory, including only, or excluding folders in a given list
'''

import os
import shutil

def copy_edits_with_filter(source_directory, mode="include"):
    # Define the list of folders to include or exclude
    folder_filter = {"alps"}

    # Define the destination path on the desktop
    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
    destination_folder = os.path.join(desktop_path, "2020 Via Alpina")

    # Create the destination folder if it doesn't exist
    os.makedirs(destination_folder, exist_ok=True)

    # Loop through each folder in the source directory
    for folder_name in os.listdir(source_directory):
        folder_path = os.path.join(source_directory, folder_name)

        # Check if it's a directory
        if os.path.isdir(folder_path):
            edits_folder = os.path.join(folder_path, "Edits")

            # Check for "include" mode
            if mode == "include" and folder_name.lower() in folder_filter:
                # Only include folders in the filter list
                if os.path.isdir(edits_folder):
                    for item in os.listdir(edits_folder):
                        item_path = os.path.join(edits_folder, item)
                        if os.path.isfile(item_path):
                            shutil.copy(item_path, destination_folder)

            # Check for "exclude" mode
            elif mode == "exclude" and folder_name.lower() not in folder_filter:
                # Exclude folders in the filter list
                if os.path.isdir(edits_folder):
                    for item in os.listdir(edits_folder):
                        item_path = os.path.join(edits_folder, item)
                        if os.path.isfile(item_path):
                            shutil.copy(item_path, destination_folder)

    print(f"Files copied to {destination_folder} based on '{mode}' mode.")

# Example usage
source_directory = "/Volumes/One Touch/2020"

# Choose mode by setting the `mode` parameter to either "include" or "exclude"
copy_edits_with_filter(source_directory, mode="include")  # Use "exclude" to switch modes