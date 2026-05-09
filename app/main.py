from __future__ import annotations
import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import ORJSONResponse, HTMLResponse
from .api.routes import router as api_router
from .logger import setup_logging
from .config import settings

# Initialize the FastAPI app
app = FastAPI(
    default_response_class=ORJSONResponse, 
    title="shellm-win-pro-ext-r2"
)

# Setup logging configuration
setup_logging()

# Mount static files
static_dir = os.path.join(os.path.dirname(__file__), "ui")
if not os.path.exists(static_dir):
    os.makedirs(static_dir, exist_ok=True)

app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/", response_class=HTMLResponse)
async def index():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    return HTMLResponse("<h1>shellm ui not found</h1>", status_code=404)

# Include the API router
app.include_router(api_router, prefix="/api")