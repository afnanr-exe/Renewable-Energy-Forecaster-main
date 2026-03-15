import os
from azure.storage.blob import BlobServiceClient

def download_aeso_data(tmp_dir="/app/data/aeso_rawcsv"):
    """
    Downloads AESO CSVs from Azure Blob Storage.
    Uses /app/data so it persists slightly better than /tmp in some containers.
    """
    os.makedirs(tmp_dir, exist_ok=True)

    # Use get() to avoid KeyError if the variable is missing
    conn = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
    if not conn:
        print("ERROR: AZURE_STORAGE_CONNECTION_STRING not found in environment variables.")
        return tmp_dir

    try:
        service = BlobServiceClient.from_connection_string(conn)
        container = service.get_container_client("aeso-data")

        print("Checking for new AESO data in Blob Storage...")
        for blob in container.list_blobs():
            path = os.path.join(tmp_dir, blob.name)

            # Only download if the file doesn't exist to save time/bandwidth
            if not os.path.exists(path):
                print(f"Downloading {blob.name}...")
                with open(path, "wb") as f:
                    data = container.download_blob(blob.name)
                    f.write(data.readall())
            else:
                pass # File already there, move on
                
    except Exception as e:
        print(f"Blob Download Error: {e}")

    return tmp_dir