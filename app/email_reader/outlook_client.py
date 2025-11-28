import msal
import requests
import os
import logging
import time
import webbrowser
from app.config import Config

logger = logging.getLogger(__name__)

class OutlookClient:
    def __init__(self):
        self.config = Config
        self.access_token = None
        
        # Determine Authentication Mode
        # Options: 'USER' (Interactive/Device Code) or 'SERVICE' (Client Credentials)
        # Default to 'USER' to support both Personal and Corporate accounts interactively
        self.auth_type = os.getenv("AUTH_TYPE", "USER").upper()
        
        # Determine Authority
        # For personal accounts (@live, @outlook, @hotmail), we MUST use 'consumers' or 'common'.
        target_email = os.getenv("TARGET_USER_EMAIL", "").lower()
        is_personal = any(domain in target_email for domain in ["@live.", "@outlook.", "@hotmail.", "@gmail."])
        
        if is_personal:
            self.authority = "https://login.microsoftonline.com/consumers"
            logger.info("Detected personal email. Using 'consumers' authority.")
        else:
            self.authority = self.config.AZURE_AUTHORITY
            logger.info(f"Using configured authority: {self.authority}")

        # Token Cache Logic
        self.cache_filename = "token_cache.bin"
        self.cache = msal.SerializableTokenCache()
        if os.path.exists(self.cache_filename):
            with open(self.cache_filename, "r") as f:
                self.cache.deserialize(f.read())
        
        # Initialize MSAL App
        # We use PublicClientApplication for Device Code Flow (User Mode)
        # We use ConfidentialClientApplication for Client Credentials (Service Mode)
        
        if self.auth_type == "SERVICE" and self.config.AZURE_CLIENT_SECRET:
            self.app = msal.ConfidentialClientApplication(
                client_id=self.config.AZURE_CLIENT_ID,
                client_credential=self.config.AZURE_CLIENT_SECRET,
                authority=self.authority,
                token_cache=self.cache
            )
            self.is_confidential = True
            logger.info("Initialized in SERVICE mode (Client Credentials).")
        else:
            self.app = msal.PublicClientApplication(
                client_id=self.config.AZURE_CLIENT_ID,
                authority=self.authority,
                token_cache=self.cache
            )
            self.is_confidential = False
            logger.info("Initialized in USER mode (Device Code Flow).")

    def authenticate(self):
        """Authenticates using the appropriate flow."""
        # 1. Try Cache
        accounts = self.app.get_accounts()
        if accounts:
            result = self.app.acquire_token_silent(self.config.SCOPES, account=accounts[0])
            if result and "access_token" in result:
                self.access_token = result["access_token"]
                logger.info("Authentication successful (from cache).")
                return

        # 2. Acquire New Token
        if self.is_confidential:
            # Daemon App (Client Credentials)
            logger.info("Attempting Client Credentials Flow...")
            result = self.app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
        else:
            # User App (Device Code Flow) - Works for both Personal and Corporate
            logger.info("Attempting Device Code Flow...")
            flow = self.app.initiate_device_flow(scopes=self.config.SCOPES)
            if "user_code" not in flow:
                raise Exception(f"Failed to create device flow. Error: {flow.get('error')}")

            print("\n" + "#" * 50)
            print(f"⚠️  AUTHENTICATION REQUIRED ⚠️")
            print(f"Open this URL: {flow['verification_uri']}")
            print(f"Enter this code: {flow['user_code']}")
            print("#" * 50 + "\n")
            
            # Try to open browser
            webbrowser.open(flow['verification_uri'])
            
            result = self.app.acquire_token_by_device_flow(flow)

        if "access_token" in result:
            self.access_token = result["access_token"]
            # Save cache to file
            if self.cache.has_state_changed:
                with open(self.cache_filename, "w") as f:
                    f.write(self.cache.serialize())
            logger.info("Authentication successful.")
        else:
            error = result.get('error')
            desc = result.get('error_description')
            logger.error(f"Authentication failed: {error} - {desc}")
            raise Exception(f"Could not authenticate: {desc}")

    def get_messages(self, subject_filter=None):
        """Fetches messages from the inbox."""
        if not self.access_token:
            self.authenticate()

        headers = {
            'Authorization': 'Bearer ' + self.access_token,
            'Content-Type': 'application/json'
        }

        # For User Mode (Personal or Corporate Interactive), ALWAYS use /me
        # Client Credentials (Service Mode) requires /users/{id}
        if self.is_confidential:
             target_user = os.getenv("TARGET_USER_EMAIL")
             if not target_user:
                 raise Exception("TARGET_USER_EMAIL is required for Client Credentials flow.")
             url = f"{self.config.GRAPH_API_ENDPOINT}/users/{target_user}/messages"
        else:
             url = f"{self.config.GRAPH_API_ENDPOINT}/me/messages"

        query_params = {
            '$top': 10,
            '$select': 'id,subject,hasAttachments,from,receivedDateTime,isRead,body',
            '$filter': 'hasAttachments eq true and isRead eq false'
        }
        
        if subject_filter:
            query_params['$filter'] += f" and contains(subject, '{subject_filter}')"

        response = requests.get(url, headers=headers, params=query_params)
        
        if response.status_code == 200:
            return response.json().get('value', [])
        else:
            logger.error(f"Error fetching messages: {response.text}")
            return []

    def download_attachments(self, message_id, save_path):
        """Downloads attachments for a specific message."""
        if not self.access_token:
            self.authenticate()

        headers = {'Authorization': 'Bearer ' + self.access_token}
        
        if self.is_confidential:
            target_user = os.getenv("TARGET_USER_EMAIL")
            base_url = f"{self.config.GRAPH_API_ENDPOINT}/users/{target_user}"
        else:
            base_url = f"{self.config.GRAPH_API_ENDPOINT}/me"

        url = f"{base_url}/messages/{message_id}/attachments"

        response = requests.get(url, headers=headers)
        
        saved_files = []
        if response.status_code == 200:
            attachments = response.json().get('value', [])
            for att in attachments:
                if att['@odata.type'] == '#microsoft.graph.fileAttachment':
                    filename = att['name']
                    if filename.endswith(('.xlsx', '.xls')):
                        content = att['contentBytes']
                        import base64
                        file_content = base64.b64decode(content)
                        
                        full_path = os.path.join(save_path, filename)
                        with open(full_path, 'wb') as f:
                            f.write(file_content)
                        saved_files.append(full_path)
                        logger.info(f"Downloaded: {filename}")
        else:
            logger.error(f"Error fetching attachments: {response.text}")
            
        return saved_files

    def mark_as_read(self, message_id):
        """Marks a message as read."""
        if not self.access_token:
            self.authenticate()

        headers = {
            'Authorization': 'Bearer ' + self.access_token,
            'Content-Type': 'application/json'
        }
        
        if self.is_confidential:
            target_user = os.getenv("TARGET_USER_EMAIL")
            base_url = f"{self.config.GRAPH_API_ENDPOINT}/users/{target_user}"
        else:
            base_url = f"{self.config.GRAPH_API_ENDPOINT}/me"

        url = f"{base_url}/messages/{message_id}"
        
        payload = {'isRead': True}

        response = requests.patch(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            logger.info(f"Message {message_id} marked as read.")
        else:
            logger.error(f"Error marking message as read: {response.text}")

