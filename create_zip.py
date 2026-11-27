"""Create a zip archive of the entire CarePulse project (excluding the virtual environment) and place it in the artifact directory.
The script walks the project folder, adds every file except .venv, __pycache__, instance, and .git, and writes `carepulseproject.zip`.
"""
import os, zipfile, pathlib, sys

PROJECT_ROOT = r"C:\Users\ASUS\.gemini\antigravity\scratch\carepulse-hospital"
OUTPUT_ZIP = r"C:\Users\ASUS\.gemini\antigravity\brain\f4b568ce-4406-4f11-b0e6-bbfc93b262f4\carepulseproject.zip"

exclude_dirs = {'.venv', '__pycache__', 'instance', '.git'}

with zipfile.ZipFile(OUTPUT_ZIP, 'w', zipfile.ZIP_DEFLATED) as zipf:
    for root, dirs, files in os.walk(PROJECT_ROOT):
        # Remove excluded dirs from traversal
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for file in files:
            file_path = os.path.join(root, file)
            # Compute archive name relative to project root
            arcname = os.path.relpath(file_path, PROJECT_ROOT)
            zipf.write(file_path, arcname)

print('ZIP created at', OUTPUT_ZIP)
