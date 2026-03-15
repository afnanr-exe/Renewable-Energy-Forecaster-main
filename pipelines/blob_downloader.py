import os
from azure.storage.blob import BlobServiceClient

def download_aeso_data(tmp_dir="/app/data/aeso_rawcsv"):
    os.makedirs(tmp_dir, exist_ok=True)
    conn = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
    if not conn:
        return tmp_dir

    try:
        service = BlobServiceClient.from_connection_string(conn)
        container = service.get_container_client("aeso-data")
        for blob in container.list_blobs():
            path = os.path.join(tmp_dir, blob.name)
            if not os.path.exists(path):
                with open(path, "wb") as f:
                    f.write(container.download_blob(blob.name).readall())
    except Exception as e:
        print(f"Blob Error: {e}")
    return tmp_dir