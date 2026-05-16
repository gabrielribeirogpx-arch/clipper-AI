from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.api.upload import router as upload_router
from app.api.timeline import router as timeline_router

app = FastAPI()

# =========================================
# CORS
# =========================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================================
# ROUTES
# =========================================

app.include_router(upload_router)
app.include_router(timeline_router)

# =========================================
# STATIC FILES
# =========================================

app.mount(
    "/media",
    StaticFiles(directory="app/clips"),
    name="media"
)

# =========================================
# HEALTH CHECK
# =========================================

@app.get("/")
def root():
    return {
        "status": "running"
    }