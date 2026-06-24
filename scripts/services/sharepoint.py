from office365.sharepoint.client_context import ClientContext
from office365.runtime.auth.user_credential import UserCredential
import io
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

SHAREPOINT_SITE = os.getenv("SHAREPOINT_SITE")
EXCEL_FILE_PATH = os.getenv("EXCEL_FILE_PATH")
USERNAME = os.getenv("SHAREPOINT_USERNAME")
PASSWORD = os.getenv("SHAREPOINT_PASSWORD")

def fetch_excel_data():
    ctx = ClientContext(SHAREPOINT_SITE).with_credentials(UserCredential(USERNAME, PASSWORD))
    file = ctx.web.get_file_by_server_relative_url(EXCEL_FILE_PATH)
    file_content = io.BytesIO()
    file.download(file_content).execute_query()
    file_content.seek(0)  # Revenir au début du buffer
    df = pd.read_excel(file_content)
    return df.head(10).to_dict(orient='records')
