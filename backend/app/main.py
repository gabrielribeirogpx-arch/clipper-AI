from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.api.upload import router as upload_router
from app.api.timeline import router as timeline_router

app = FastAPI()

app.include_router(upload_router)
app.include_router(timeline_router)
app.mount("/media", StaticFiles(directory="app/clips"), name="media")

@app.get("/")
def root():
    return {"status": "running"}
