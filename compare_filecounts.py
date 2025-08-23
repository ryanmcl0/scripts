import os

folder1 = ""
folder2 = ""

def list_all_files(base_path):
    """
    Returns a set of relative file paths (from base_path) for all files inside base_path.
    """
    files_set = set()
    for root, dirs, files in os.walk(base_path):
        for f in files:
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, base_path)
            files_set.add(rel_path)
    return files_set

if __name__ == "__main__":
    files_in_1 = list_all_files(folder1)
    files_in_2 = list_all_files(folder2)

    missing_in_1 = files_in_2 - files_in_1

    if missing_in_1:
        print(f"Files present in '{folder2}' but missing in '{folder1}':\n")
        for f in sorted(missing_in_1):
            print(f)
    else:
        print("No files are missing from the first folder compared to the second.")
