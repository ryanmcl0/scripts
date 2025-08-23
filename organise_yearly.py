'''
Restructre organisation of phone photos dumped into one folder by year
'''

import os
import re
import shutil

# Path to your folder
source_folder = "/Volumes/RYAN/Phone camera"

# Regular expression to match filenames starting with YYYYMMDD_
date_pattern = re.compile(r"^(\d{4})\d{4}_")

# Only loop through files (not directories) in the top-level folder
for filename in os.listdir(source_folder):
    filepath = os.path.join(source_folder, filename)

    if os.path.isfile(filepath):
        match = date_pattern.match(filename)
        if match:
            year = match.group(1)
            year_folder = os.path.join(source_folder, year)
            
            # Create year folder if it doesn't exist
            os.makedirs(year_folder, exist_ok=True)
            
            # Move the file into the year folder
            destination = os.path.join(year_folder, filename)
            shutil.move(filepath, destination)
            print(f"Moved: {filename} -> {year}/")
        else:
            print(f"Skipped (no date): {filename}")
