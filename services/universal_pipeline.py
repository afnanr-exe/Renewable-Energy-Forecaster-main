import os
import pandas as pd
import yaml
from pipelines.ieso_pipeline import build_ieso_master
from pipelines.aeso_pipeline import build_aeso_master

# BASE_DIR is root/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AZURE_MOUNT_DIR = "/app/output"

class UniversalPipeline:
    def __init__(self):
        self.config_path = os.path.join(BASE_DIR, "config.yaml")
        with open(self.config_path, "r") as f:
            self.config = yaml.safe_load(f)
        self.output_base = AZURE_MOUNT_DIR

    def _get_paths(self, market: str):
        market_dir = os.path.join(self.output_base, market)
        os.makedirs(market_dir, exist_ok=True)
        return {"market_output_dir": market_dir}

    def run_market(self, market, city, upload_mode=None, file_format=None, files=None, timezone=None):
        try:
            paths = self._get_paths(market)
            out_dir = paths["market_output_dir"]

            if market == "ieso":
                xml_dir = self.config["markets"]["ieso"]["xml_dir"] # "/app/data/ieso/xml/"
                master_path = build_ieso_master(xml_dir, out_dir, city, timezone or "UTC")
            elif market == "aeso":
                from pipelines.blob_downloader import download_aeso_data
                input_dir = download_aeso_data()
                master_path = build_aeso_master(input_dir, out_dir, city, "America/Edmonton")
            elif market == "upload":
                from pipelines.user_pipeline import build_user_master
                master_path = build_user_master(upload_mode, file_format, files, out_dir, city, timezone)

            # Standard Model Processing
            df = pd.read_csv(master_path)
            # ... (Logic to run your regression_engine.run_both_models here) ...
            
            print(f"Pipeline finished for {market}")
            return {"master_path": master_path}
        except Exception as e:
            print(f"Pipeline Error: {e}")
            return {"error": str(e)}