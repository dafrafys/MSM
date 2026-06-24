from office365.sharepoint.client_context import ClientContext
from office365.runtime.auth.user_credential import UserCredential
from dotenv import load_dotenv
import os

load_dotenv()

# Configuration (à adapter)
site_url = os.getenv("SHAREPOINT_SITE")
username = os.getenv("SHAREPOINT_USERNAME")
password = os.getenv("SHAREPOINT_PASSWORD")
sharepoint_file_relative_url = os.getenv("EXCEL_FILE_PATH")
local_folder = "./data"
local_file_name = "rapport_mc.xlsx"

# Vérification variables d'environnement
required_vars = [site_url, username, password, sharepoint_file_relative_url]
if not all(required_vars):
    raise ValueError("Une ou plusieurs variables d'environnement SharePoint ne sont pas définies")

# Connexion au site SharePoint
ctx = ClientContext(site_url).with_credentials(UserCredential(username, password))

# Prépare le chemin local
os.makedirs(local_folder, exist_ok=True)
local_file_path = os.path.join(local_folder, local_file_name)

# Télécharger le fichier
try:
    with open(local_file_path, "wb") as local_file:
        ctx.web.get_file_by_server_relative_url(sharepoint_file_relative_url).download(local_file).execute_query()
    print(f"Fichier téléchargé dans : {local_file_path}")
except Exception as e:
    print(f"Erreur lors du téléchargement : {e}")
