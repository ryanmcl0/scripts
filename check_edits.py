'''
Check which RAW folders also contain an edits folder
'''

import os

def check_edits_subfolder(directory_path):
    # List to store folders that are missing the "Edits" subfolder
    missing_edits = []

    # Loop through each folder in the specified directory
    for folder_name in os.listdir(directory_path):
        folder_path = os.path.join(directory_path, folder_name)

        # Check if the item is a folder
        if os.path.isdir(folder_path):
            edits_path = os.path.join(folder_path, "Edits")

            # Check if "Edits" subfolder exists
            if not os.path.isdir(edits_path):
                missing_edits.append(folder_name)

    # Display results
    if missing_edits:
        print("The following folders are missing the 'Edits' subfolder:")
        for folder in missing_edits:
            print(f"- {folder}")
    else:
        print("All folders contain an 'Edits' subfolder.")

# Example usage
directory_path = "/Volumes/One Touch/2020"
check_edits_subfolder(directory_path)