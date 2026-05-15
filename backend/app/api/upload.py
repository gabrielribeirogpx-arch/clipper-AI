from fastapi import APIRouter, UploadFile, File
from app.jobs.process_video_job import process_video
import os
import uuid
import shutil

router = APIRouter()

UPLOAD_DIR = "app/uploads"

os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload")
async def upload_video(file: UploadFile = File(...)):

    file_id = str(uuid.uuid4())

    filepath = f"{UPLOAD_DIR}/{file_id}.mp4"

    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    transcription = process_video(filepath)

    return {
    "message": "upload success",
    "file_id": file_id,
    "path": filepath,
    "transcription": transcription["text"],
"hooks": transcription["hooks"]
}