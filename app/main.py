import os
from enum import Enum
from typing import List, Optional

# Added BackgroundTasks to imports
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles

from services.universal_pipeline import UniversalPipeline

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

DEFAULT_IESO_CITY = "Goderich"
DEFAULT_AESO_CITY = "Red Deer"

PROVINCE_TIMEZONE: dict[Province, str] = {
    Province.alberta: "America/Edmonton",
    Province.ontario: "UTC",
    Province.other:   "UTC",
}

def to_url_path(abs_path: str) -> str:
    if not abs_path: return abs_path
    try:
        rel = os.path.relpath(abs_path, BASE_DIR).replace("\\", "/")
        return f"/{rel}"
    except ValueError:
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

# ── UPDATED API endpoints ──────────────────────────────────────

@app.get("/run-ieso")
async def run_ieso(background_tasks: BackgroundTasks):
    # Runs in background to prevent Azure 504 Timeout
    background_tasks.add_task(pipeline.run_market, "ieso", city=DEFAULT_IESO_CITY)
    return {"status": "started", "message": "IESO Pipeline running in background. Check Azure logs."}

@app.get("/run-aeso")
async def run_aeso(background_tasks: BackgroundTasks):
    # Runs in background to prevent Azure 504 Timeout
    background_tasks.add_task(pipeline.run_market, "aeso", city=DEFAULT_AESO_CITY)
    return {"status": "started", "message": "AESO Pipeline running in background. Check Azure logs."}

@app.post("/run-upload")
def run_upload(
    upload_mode:   UploadMode    = Form(...),
    market_format: MarketFormat  = Form(...),
    province:      Province      = Form(...),
    other_city:    Optional[str] = Form(None),
    files:         List[UploadFile] = File(...),
):
    # Keeping upload synchronous so user sees plots immediately
    file_format = "csv" if market_format == MarketFormat.aeso else "xml"
    if province == Province.ontario: final_city = DEFAULT_IESO_CITY
    elif province == Province.alberta: final_city = DEFAULT_AESO_CITY
    else:
        if not other_city: raise HTTPException(status_code=400, detail="Provide a city name.")
        final_city = other_city

    tz = PROVINCE_TIMEZONE[province]
    return convert_paths(pipeline.run_market(
        "upload", city=final_city, upload_mode=upload_mode.value,
        file_format=file_format, files=files, timezone=tz
    ))

@app.get("/run-forecast")
def run_forecast_endpoint(market: str, city: str):
    from services.forecast_service import run_forecast
    try:
        return run_forecast(market, city)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── Static file mounts ─────────────────────────────────────────
_output_dir   = "/app/output" # Fixed to match Azure Mount Path
_frontend_dir = os.path.join(BASE_DIR, "frontend")

os.makedirs(_output_dir, exist_ok=True)
app.mount("/output", StaticFiles(directory=_output_dir), name="output")
app.mount("/", StaticFiles(directory=_frontend_dir, html=True), name="frontend")