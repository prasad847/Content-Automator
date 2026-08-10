import os
import json
from googleapiclient.discovery import build
from google.oauth2 import service_account
from dotenv import load_dotenv
import io
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.http import MediaFileUpload

load_dotenv()

INPUT_FOLDER_ID = os.getenv("GOOGLE_DRIVE_INPUT_FOLDER_ID")
CREDENTIALS_FILE = "google_drive_credentials.json"
PROCESSED_FILE = "processed_files.json"

SCOPES = ["https://www.googleapis.com/auth/drive"]  # changed from drive.readonly - now needs write access
# Only these mimetypes count as "audio to process"
AUDIO_MIMETYPES = {
    "audio/mpeg",   # .mp3
    "audio/wav",
    "audio/x-wav",
    "audio/mp4",    # .m4a
    "audio/x-m4a",
}


def get_drive_service():
    """Authenticate and return a connected Google Drive client."""
    creds = service_account.Credentials.from_service_account_file(
        CREDENTIALS_FILE, scopes=SCOPES
    )
    return build("drive", "v3", credentials=creds)


def load_processed_ids():
    """Read the list of file IDs we've already handled."""
    with open(PROCESSED_FILE, "r") as f:
        return json.load(f)


def save_processed_id(file_id):
    """Add a file ID to the processed list so we never redo it."""
    ids = load_processed_ids()
    ids.append(file_id)
    with open(PROCESSED_FILE, "w") as f:
        json.dump(ids, f)


def list_new_audio_files():
    """Return audio files in the Input folder that we haven't processed yet."""
    service = get_drive_service()
    processed_ids = load_processed_ids()

    results = service.files().list(
        q=f"'{INPUT_FOLDER_ID}' in parents and trashed=false",
        fields="files(id, name, mimeType)"
    ).execute()

    all_files = results.get("files", [])

    new_audio_files = [
        f for f in all_files
        if f["id"] not in processed_ids and f["mimeType"] in AUDIO_MIMETYPES
    ]

    return new_audio_files

def download_file(file_id, file_name):
    """Download a Drive file into the app folder and return its local path."""
    service = get_drive_service()
    request = service.files().get_media(fileId=file_id)

    local_path = file_name  # saves into app/ folder, same name as in Drive
    file_stream = io.FileIO(local_path, "wb")
    downloader = MediaIoBaseDownload(file_stream, request)

    done = False
    while not done:
        status, done = downloader.next_chunk()

    return local_path

def upload_file_to_drive(local_path, file_name):
    """Upload a local file to the Input Drive folder. Returns the new file's Drive ID."""
    service = get_drive_service()
    file_metadata = {"name": file_name, "parents": [INPUT_FOLDER_ID]}
    media = MediaFileUpload(local_path, resumable=True)
    uploaded = service.files().create(body=file_metadata, media_body=media, fields="id").execute()
    return uploaded.get("id")