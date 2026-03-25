import sys

file_path = "c:/Users/artar/Downloads/Api META/portal_ia.py"

with open(file_path, "rb") as f:
    lines = f.readlines()

# Truncate to the original 175 lines to remove the corrupted text
original_lines = lines[:175]

with open(file_path, "wb") as f:
    f.writelines(original_lines)
