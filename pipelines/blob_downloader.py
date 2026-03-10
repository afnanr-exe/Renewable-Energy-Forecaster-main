import os
from azure.storage.blob import BlobServiceClient

def download_aeso_data(tmp_dir="/tmp/aeso_rawcsv"):
    os.makedirs(tmp_dir, exist_ok=True)

    conn = os.environ["AZURE_STORAGE_CONNECTION_STRING"]
    service = BlobServiceClient.from_connection_string(conn)

    container = service.get_container_client("aeso-data")

    for blob in container.list_blobs():
        path = os.path.join(tmp_dir, blob.name)

        with open(path, "wb") as f:
            data = container.download_blob(blob.name)
            f.write(data.readall())

    return tmp_dir