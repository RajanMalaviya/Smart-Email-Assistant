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
def generate_response(email_id: str):
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

    # Step 1: Generate draft
    draft = responder_chain.invoke({
        "sender": sender,
        "recipient": recipient,
        "subject": subject,
        "email_body": body
    }).content

    # Step 2: Human-in-the-loop
    print("\n----- Draft Reply -----\n")
    print(draft)
    print("\n-----------------------\n")

    choice = input("Do you want to (s)end, (e)dit, or (c)ancel? ")

    if choice.lower() == "e":
        print("Enter your edited response (single line, or paste text):")
        draft = input("> ")

    if choice.lower() in ["s", "e"]:
        result = send_email(sender, subject, draft)
        responses_collection.insert_one({
            "email_id": email_id,
            "thread_id": email_doc.get("thread_id"),
            "to": sender,
            "from": recipient,
            "subject": subject,
            "body": draft,
            "status": "sent",
            "edited_by_human": choice.lower() == "e",
            "created_at": datetime.datetime.utcnow(),
            "sent_at": datetime.datetime.utcnow(),
            "gmail_response": result
        })
        print("✅ Email sent and response stored in DB")
    else:
        print("❌ Action cancelled.")


if __name__ == "__main__":
    email_id = input("Enter email ID (_id from DB) to reply: ")
    generate_response(email_id)
