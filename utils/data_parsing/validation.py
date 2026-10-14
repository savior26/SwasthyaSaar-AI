from pathlib import Path
import os

from fastapi import UploadFile

MAX_FILE_SIZE = 10 * 1024 * 1024   # 10MB

def validate_file(file: UploadFile):
    """
    Validate file extension and file size.
    """
    ALLOWED_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png', '.docx', '.txt'}

    # 1. Validate Extension using file.filename
    if not file.filename:
        raise ValueError("Filename is empty.")

    extension = Path(file.filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file format '{extension}'. Allowed formats: "
            f"{', '.join(ext.upper().lstrip('.') for ext in ALLOWED_EXTENSIONS)}"
        )

    # 2. Validate File Size using file.size
    if file.size and file.size > MAX_FILE_SIZE:
        max_mb = MAX_FILE_SIZE // (1024 * 1024)
        raise ValueError(f"File too large. Maximum allowed size is {max_mb} MB.")

    return True