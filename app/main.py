import os
from enum import Enum
from typing import List, Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles

# Imports from the root-level folders
from services.universal_pipeline import UniversalPipeline

# BASE_DIR is the root project folder (one level up from /app)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = FastAPI()
pipeline = UniversalPipeline()

class UploadMode(str, Enum):
    single = "single"
    multi  = "multi"

class MarketFormat(str, Enum):
    aeso = "aeso"
    ieso = "ieso"

class Province(str, Enum):
    alberta = "alberta"
    ontario = "ontario"
    other   = "other"

PROVINCE_TIMEZONE = {
    Province.alberta: "America/Edmonton",
    Province.ontario: "UTC",
    Province.other:   "UTC",
}

def to_url_path(abs_path: str) -> str:
    if not abs_path: return abs_path
    try:
        # Converts /app/output/plots/... to /output/plots/... for the browser
        rel = os.path.relpath(abs_path, "/app").replace("\\", "/")
        return f"/{rel}"
    except:
        return abs_path

def convert_paths(result: dict) -> dict:
    for fuel in ("wind", "solar"):
        fuel_data = result.get(fuel)
        if not fuel_data or fuel_data.get("skipped"): continue
        for model in ("linear", "polynomial"):
            m = fuel_data.get(model) or {}
            for key in ("scatter_plot", "timeseries_plot"):
                if key in m: m[key] = to_url_path(m[key])
    for key in ("master_path", "wind_csv", "solar_csv"):
        if key in result: result[key] = to_url_path(result[key])
    return result

@app.get("/run-ieso")
async def run_ieso(background_tasks: BackgroundTasks):
    background_tasks.add_task(pipeline.run_market, "ieso", city="Goderich")
    return {"status": "started", "message": "IESO Pipeline started. Check Azure logs for progress."}

@app.get("/run-aeso")
async def run_aeso(background_tasks: BackgroundTasks):
    background_tasks.add_task(pipeline.run_market, "aeso", city="Red Deer")
    return {"status": "started", "message": "AESO Pipeline started. Downloading blobs and processing..."}

@app.post("/run-upload")
def run_upload(
    upload_mode: UploadMode = Form(...),
    market_format: MarketFormat = Form(...),
    province: Province = Form(...),
    other_city: Optional[str] = Form(None),
    files: List[UploadFile] = File(...),
):
    tz = PROVINCE_TIMEZONE[province]
    # Upload remains synchronous so the user gets plots back immediately
    res = pipeline.run_market(
        "upload", city=other_city or "Default", upload_mode=upload_mode.value,
        file_format="csv" if market_format == "aeso" else "xml",
        files=files, timezone=tz
    )
    return convert_paths(res)

# Absolute paths for Azure Mounts
_output_dir = "/app/output"
_frontend_dir = os.path.join(BASE_DIR, "frontend")

os.makedirs(_output_dir, exist_ok=True)
app.mount("/output", StaticFiles(directory=_output_dir), name="output")
app.mount("/", StaticFiles(directory=_frontend_dir, html=True), name="frontend")