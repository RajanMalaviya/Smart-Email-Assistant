from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import os
import datetime
from typing import Dict, Any
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
from email.mime.text import MIMEText
import base64
from bson import ObjectId

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from config.settings import MONGO_URI as SETTINGS_MONGO_URI, MONGO_DB as SETTINGS_MONGO_DB, MONGO_COLLECTION as SETTINGS_MONGO_COLLECTION

MONGO_URI = SETTINGS_MONGO_URI
MONGO_DB = SETTINGS_MONGO_DB
MONGO_COLLECTION = SETTINGS_MONGO_COLLECTION
token_path = "./services/token.json"
creds_path = "./services/credentials.json"

try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    client.server_info()  # verify connection
    db = client[MONGO_DB]
    emails_collection = db[MONGO_COLLECTION]
    responses_collection = db["responses"]
    print("Mongodb connected")
    
except ServerSelectionTimeoutError as e:
    print("Mongodb connection failed")
    raise e

# Gmail API Setup
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

def get_gmail_service():
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w") as token:
            token.write(creds.to_json())
    service = build("gmail", "v1", credentials=creds)
    return service

def send_email(to: str, subject: str, body: str):
    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

    service = get_gmail_service()
    sent = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    return sent


# Gemini + LangChain Setup
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=os.getenv("GEMINI_API_KEY"),
    temperature=0.4
)

prompt = ChatPromptTemplate.from_template("""
You are a Smart AI email responder.
Write a professional, polite, and concise reply to the email below.

From: {sender}
To: {recipient}
Subject: {subject}

Email Body:
{email_body}

Reply in 3-5 sentences and ensure clarity and relevance.
Your response should address the main points of the email and provide any necessary information or clarification.
Reply:
""")

# Build Runnable pipeline
responder_chain = (
    {"sender": RunnablePassthrough(),
     "recipient": RunnablePassthrough(),
     "subject": RunnablePassthrough(),
     "email_body": RunnablePassthrough()}
    | prompt
    | llm
)

# Responder Agent
def generate_response(email_id: str, human_input: str = None, send_email_flag: bool = True):
    """
    Generate and optionally send a response to an email.

    Args:
        email_id (str): MongoDB ObjectId of the email.
        human_input (str, optional): Edited draft to merge with AI draft.
        send_email_flag (bool): If True, send the email. If False, just generate draft.
    
    Returns:
        dict: Contains merged draft, email metadata, and status info.
    """
    try:
        oid = ObjectId(email_id)
    except Exception:
        raise ValueError("Invalid ObjectId format")
    
    email_doc: Dict[str, Any] = emails_collection.find_one({"_id": oid})
    if not email_doc:
        raise ValueError("Email not found!")

    sender = email_doc.get("from", "")
    recipient = email_doc.get("to", [])[0] if email_doc.get("to") else "unknown@example.com"
    subject = "Re: " + (email_doc.get("subject") or "No Subject")
    body = email_doc.get("body_plain") or email_doc.get("snippet") or ""

    # Step 1: Generate draft using AI
    ai_draft = responder_chain.invoke({
        "sender": sender,
        "recipient": recipient,
        "subject": subject,
        "email_body": body
    }).content

    # Step 2: Merge AI draft with human input if provided
    if human_input:
        # Merge: AI draft first, then human edits separated by a line
        if human_input=="string":
            human_input=""
        merged_draft = f"{ai_draft}\n{human_input}"
    else:
        merged_draft = ai_draft

    # Step 3: Optionally send email
    result = None
    status = "draft_generated"
    if send_email_flag:
        result = send_email(sender, subject, merged_draft)
        responses_collection.insert_one({
            "email_id": email_id,
            "thread_id": email_doc.get("thread_id"),
            "to": sender,
            "from": recipient,
            "subject": subject,
            "body": merged_draft,
            "status": "sent",
            "edited_by_human": bool(human_input),
            "created_at": datetime.datetime.utcnow(),
            "sent_at": datetime.datetime.utcnow(),
            "gmail_response": result
        })
        status = "sent"

    return {
        "email_id": email_id,
        "to": sender,
        "from": recipient,
        "subject": subject,
        "draft": merged_draft,
        "status": status,
        "gmail_response": result
    }
