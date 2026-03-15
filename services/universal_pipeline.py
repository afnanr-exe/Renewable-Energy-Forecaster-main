import os
import pandas as pd
import yaml
from fastapi import HTTPException

from models.regression_engine import run_both_models
from pipelines.ieso_pipeline import build_ieso_master
from pipelines.aeso_pipeline import build_aeso_master

# Absolute path where your Azure File Share is mounted
AZURE_MOUNT_DIR = "/app/output"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class UniversalPipeline:
    def __init__(self):
        # Config stays in the app folder
        self.config_path = os.path.join(BASE_DIR, "config.yaml")
        with open(self.config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        # Output base is the permanent Azure File Share
        self.output_base = AZURE_MOUNT_DIR
        os.makedirs(self.output_base, exist_ok=True)

    def _get_paths(self, market: str):
        market_dir = os.path.join(self.output_base, market)
        os.makedirs(market_dir, exist_ok=True)
        return {"market_output_dir": market_dir}

    def _run_model_safe(self, csv_path: str, target: str, features: list[str], label: str) -> dict:
        try:
            return run_both_models(
                csv_path=csv_path,
                target=target,
                features=features,
                label=label,
            )
        except Exception as e:
            print(f"Model Error for {label}: {e}")
            return {"skipped": True, "reason": str(e)}

    def run_market(self, market: str, city: str, upload_mode=None, file_format=None, files=None, timezone=None):
        """Wrapper for background tasks to prevent API hangs."""
        try:
            return self._run_market_inner(market, city, upload_mode, file_format, files, timezone)
        except Exception as e:
            print(f"PIPELINE CRASHED: {e}")

    def _run_market_inner(self, market: str, city: str, upload_mode, file_format, files, timezone=None):
        paths = self._get_paths(market)
        market_output_dir = paths["market_output_dir"]

        # 1. DATA FETCHING PHASE
        if market == "upload":
            from pipelines.user_pipeline import build_user_master
            master_path = build_user_master(
                upload_mode=upload_mode, file_format=file_format,
                files=files, output_dir=market_output_dir,
                city=city, timezone=timezone or "UTC"
            )
        elif market == "ieso":
            # xml_dir comes from config.yaml (e.g., /app/data/ieso/xml/)
            xml_dir = self.config["markets"]["ieso"]["xml_dir"]
            tz = self.config["markets"]["ieso"].get("timezone", "UTC")
            master_path = build_ieso_master(xml_dir=xml_dir, output_dir=market_output_dir, city=city, timezone=tz)
        elif market == "aeso":
            from pipelines.blob_downloader import download_aeso_data
            input_dir = download_aeso_data() # Pulls from Blob Storage
            tz = self.config["markets"]["aeso"].get("timezone", "America/Edmonton")
            master_path = build_aeso_master(input_dir=input_dir, output_dir=market_output_dir, city=city, timezone=tz)

        # 2. DATA PROCESSING PHASE
        df = pd.read_csv(master_path)
        df["timestamp"] = pd.to_datetime(df["timestamp"])

        # Prepare CSVs for models
        wind_cols = ["timestamp", "Wind", "temperature_2m", "windspeed_10m", "winddirection_10m"]
        solar_cols = ["timestamp", "Solar", "temperature_2m", "cloudcover", "shortwave_radiation"]

        wind_csv_path = os.path.join(market_output_dir, "wind_model_data.csv")
        solar_csv_path = os.path.join(market_output_dir, "solar_model_data.csv")

        if "Wind" in df.columns:
            df.dropna(subset=["Wind"])[wind_cols].to_csv(wind_csv_path, index=False)
        if "Solar" in df.columns:
            df.dropna(subset=["Solar"])[solar_cols].to_csv(solar_csv_path, index=False)

        # 3. MODEL TRAINING PHASE
        wind_results = self._run_model_safe(wind_csv_path, "Wind", wind_cols[2:], f"{market.upper()}_Wind")
        solar_results = self._run_model_safe(solar_csv_path, "Solar", solar_cols[2:], f"{market.upper()}_Solar")

        print(f"SUCCESS: Pipeline for {market} complete. Files in {market_output_dir}")
        return {"status": "Complete", "master": master_path}