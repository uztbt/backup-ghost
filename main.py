import os
import requests
from datetime import datetime, timezone, timedelta
from google.cloud import secretmanager
from google.cloud import storage

def backup_ghost(event, context):
  # Get values of environment variables
  project_id = os.environ.get("PROJECT_ID")
  secret_name = os.environ.get("SECRET_NAME")
  ghost_username = os.environ.get("GHOST_USERNAME")
  backup_bucket_name = os.environ.get("BACKUP_BUCKET_NAME")
  origin = os.environ.get("ORIGIN")
  ghost_base_url = os.environ.get("GHOST_BASE_URL")
  ghost_session_url = f"{ghost_base_url}/ghost/api/v3/admin/session/"
  ghost_db_url = f"{ghost_base_url}/ghost/api/v3/admin/db/"
  

  # Get the secret of the Ghost user
  client = secretmanager.SecretManagerServiceClient()
  request = {"name": f"projects/{project_id}/secrets/{secret_name}/versions/latest"}
  response = client.access_secret_version(request)
  ghost_password = response.payload.data.decode("UTF-8")

  # Get a backup
  with requests.Session() as session:
    headers = {
      'Origin': origin
    }
    data = {
      'username': ghost_username,
      'password': ghost_password
    }
    session.post(ghost_session_url, headers=headers, data=data)
    response = session.get(ghost_db_url, headers=headers)
  backup_json = response.json()

  # Upload to the GCS bucket
  storage_client = storage.Client()
  bucket = storage_client.bucket(backup_bucket_name)
  now = datetime.now(timezone(timedelta(hours=9)))
  destination_backup_file_name = now.strftime("backup-%m-%d-%Y.json")
  blob = bucket.blob(destination_backup_file_name)
  
  blob.upload_from_string(str(backup_json), content_type='application/json')

  return f"Successfully created a backup to {backup_bucket_name}/{destination_backup_file_name}"