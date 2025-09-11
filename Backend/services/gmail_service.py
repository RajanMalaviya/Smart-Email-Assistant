import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from services.logger import get_logger

logger = get_logger(__name__)

# Gmail API Scopes
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

class GmailService:
    def __init__(self):
        self.creds = None
        self.service = None
        self.authenticate()

    def authenticate(self):
        """Authenticate Gmail API using OAuth2 and reuse token if valid"""
        token_path = "./services/token.json"
        creds_path = "./services/credentials.json"

        # Load saved credentials
        if os.path.exists(token_path):
            self.creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            logger.info("Loaded existing Gmail token.json")

        # If no valid credentials, login or refresh
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                logger.info("Refreshing expired Gmail token...")
                try:
                    self.creds.refresh(Request())
                    logger.info("Token refreshed successfully")
                except Exception as e:
                    logger.error("Failed to refresh token, performing login", exc_info=True)
                    self.creds = None
            if not self.creds:
                logger.info("Performing Gmail login via OAuth flow...")
                flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
                self.creds = flow.run_local_server(port=0)

            # Save updated credentials
            with open(token_path, "w") as token_file:
                token_file.write(self.creds.to_json())
                logger.info("Saved Gmail token.json for future runs")

        # Initialize Gmail service
        self.service = build("gmail", "v1", credentials=self.creds)
        logger.info("Gmail API service initialized successfully")

    def fetch_inbox_emails(self, max_results=10):
        """Fetch inbox emails from Gmail"""
        logger.info(f"Fetching {max_results} emails from Gmail inbox...")
        results = self.service.users().messages().list(
            userId="me",
            labelIds=["INBOX"],
            maxResults=max_results
        ).execute()

        messages = results.get("messages", [])
        emails = []
        for msg in messages:
            msg_data = self.service.users().messages().get(userId="me", id=msg["id"]).execute()
            headers = msg_data["payload"]["headers"]

            # Extract common fields
            subject = next((h["value"] for h in headers if h["name"] == "Subject"), "")
            sender = next((h["value"] for h in headers if h["name"] == "From"), "")
            snippet = msg_data.get("snippet", "")

            emails.append({
                "provider": "gmail",
                "provider_message_id": msg["id"],
                "thread_id": msg_data.get("threadId"),
                "from": sender,
                "subject": subject,
                "snippet": snippet,
                "labels": msg_data.get("labelIds", [])
            })

        logger.info(f"Fetched {len(emails)} emails successfully")
        return emails
