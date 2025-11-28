import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    # Microsoft Graph Settings
    AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
    AZURE_TENANT_ID = os.getenv("AZURE_TENANT_ID")
    AZURE_CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
    AZURE_AUTHORITY = f"https://login.microsoftonline.com/{AZURE_TENANT_ID}"
    GRAPH_API_ENDPOINT = "https://graph.microsoft.com/v1.0"
    SCOPES = ["User.Read", "Mail.Read", "Mail.ReadWrite"]

    # IMAP Settings (cPanel/Standard)
    EMAIL_PROVIDER = os.getenv("EMAIL_PROVIDER", "OUTLOOK").upper() # OUTLOOK or IMAP
    IMAP_SERVER = os.getenv("IMAP_SERVER")
    IMAP_PORT = int(os.getenv("IMAP_PORT", 993))
    IMAP_USER = os.getenv("IMAP_USER")
    IMAP_PASSWORD = os.getenv("IMAP_PASSWORD")

    # Email Settings
    EMAIL_SUBJECT_TRIGGER = os.getenv("EMAIL_SUBJECT_TRIGGER", "Procesar Archivo")
    ATTACHMENT_SAVE_PATH = os.path.join(os.getcwd(), "downloads")

    # AI Settings
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

    # Telegram Settings
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

    @staticmethod
    def validate():
        """Validates that critical configuration is present."""
        missing = []
        if not Config.AZURE_CLIENT_ID: missing.append("AZURE_CLIENT_ID")
        if not Config.AZURE_TENANT_ID: missing.append("AZURE_TENANT_ID")
        if not Config.GEMINI_API_KEY: missing.append("GEMINI_API_KEY")
        if not Config.TELEGRAM_BOT_TOKEN: missing.append("TELEGRAM_BOT_TOKEN")
        
        if missing:
            raise ValueError(f"Missing configuration variables: {', '.join(missing)}")

# Ensure download directory exists
os.makedirs(Config.ATTACHMENT_SAVE_PATH, exist_ok=True)
