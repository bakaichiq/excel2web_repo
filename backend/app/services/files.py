from pathlib import Path
import shutil
from fastapi import UploadFile
from app.core.config import settings

def ensure_dirs():
    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    Path(settings.EXPORT_DIR).mkdir(parents=True, exist_ok=True)

def save_upload(file: UploadFile, dest_path: Path) -> None:
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with dest_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)
