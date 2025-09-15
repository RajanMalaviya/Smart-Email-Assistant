# import sys

# from bson import ObjectId
# from services.gmail_service import GmailService
# from utils.parser import clean_email_text
# from services.db_service import bulk_upsert_emails, get_all_emails
# from services.logger import get_logger
# from services.classifier import classify_unclassified_emails
# from services.responder import generate_response


# logger = get_logger(__name__)

# # Helper functions
# def _truncate(text: str, max_len: int) -> str:
#     if text is None:
#         return ""
#     text = str(text).replace("\n", " ").replace("\r", " ")
#     return text if len(text) <= max_len else text[: max_len - 1] + "…"

# def _print_table(rows):
#     if not rows:
#         return
#     col_from = 28
#     col_subject = 40
#     col_snippet = 60
#     header = f"{'From':<{col_from}} | {'Subject':<{col_subject}} | {'Snippet':<{col_snippet}}"
#     separator = f"{'-'*col_from}-+-{'-'*col_subject}-+-{'-'*col_snippet}"
#     print("\nGmail Emails:")
#     print(header)
#     print(separator)
#     for row in rows:
#         from_text = _truncate(row.get('from', 'Unknown'), col_from)
#         subject_text = _truncate(row.get('subject', ''), col_subject)
#         snippet_text = _truncate(clean_email_text(row.get('snippet', '')), col_snippet)
#         print(f"{from_text:<{col_from}} | {subject_text:<{col_subject}} | {snippet_text:<{col_snippet}}")

# # Fetch & Store Emails
# def fetch_and_store_emails(max_emails_to_fetch: int = 5):
#     gmail = GmailService()
#     logger.info(f"Fetching up to {max_emails_to_fetch} emails from Gmail...")
#     gmail_emails = gmail.fetch_inbox_emails(max_results=max_emails_to_fetch)
#     logger.info(f"Fetched {len(gmail_emails)} emails from Gmail")
#     print(f"{len(gmail_emails)} email fetched" if len(gmail_emails) == 1 else f"{len(gmail_emails)} emails fetched")

#     if not gmail_emails:
#         logger.warning("No emails fetched. Exiting.")
#         return

#     logger.info("Storing fetched emails in MongoDB...")
#     result = bulk_upsert_emails(gmail_emails, provider="gmail")
#     logger.info(f"Upsert Results: {result}")
#     print("stored in mongodb")

#     _print_table(gmail_emails)

#     stored_emails = get_all_emails()
#     logger.info(f"Total stored emails in MongoDB: {len(stored_emails)}")
#     print("done")

# # Main Runner
# if __name__ == "__main__":
#     task = sys.argv[1] if len(sys.argv) > 1 else "all"

#     if task == "fetch":
#         print("📥 Running fetch mode...")
#         fetch_and_store_emails(max_emails_to_fetch=10)

#     elif task == "classify":
#         print("🔎 Running classifier mode...")
#         classify_unclassified_emails()
        
#     elif task == "respond":
#         print("✉️ Running responder mode...")  # will prompt for email ID
#         email_id = input("Enter the email ID to respond to: ").strip()
#         try:
#             generate_response(email_id)
#         except ValueError as ve:
#             print(f"Error: {ve}")

#     elif task == "all":
#         print("📥 Running fetch + classify mode...")
#         fetch_and_store_emails(max_emails_to_fetch=10)
        
#         print("\n🚀 Starting email classifier...")
#         classify_unclassified_emails()
        
#         print("✉️ Running responder mode...")  # will prompt for email ID
#         email_id = input("Enter the email ID to respond to: ").strip()
#         try:
#             generate_response(email_id)
#         except ValueError as ve:
#             print(f"Error: {ve}")

#     else:
#         print(f"⚠️ Unknown task: {task}")
#         print("Usage: python main.py [fetch|classify|all]")


from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from bson import ObjectId

from services.gmail_service import GmailService
from services.db_service import bulk_upsert_emails, get_all_emails, get_all_classified_emails
from services.classifier import classify_unclassified_emails
from services.responder import generate_response
from utils.parser import clean_email_text
from services.logger import get_logger
from fastapi.middleware.cors import CORSMiddleware
logger = get_logger(__name__)

app = FastAPI(title="Smart Email Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # your React Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models
class FetchRequest(BaseModel):
    max_emails_to_fetch: Optional[int] = 10
    
class RespondRequest(BaseModel):
    email_id: str
    draft: Optional[str] = None  # optional edited draft

class AllTasksRequest(BaseModel):
    fetch_limit: Optional[int] = 10
    respond_email_id: Optional[str] = None
    human_input: Optional[str] = None  # optional edited draft


# Routes
@app.get("/")
def root():
    return {"message": "Smart Email Assistant API is running"}

# Fetch emails and store in MongoDB
@app.post("/fetch")
def fetch_emails(request: FetchRequest):
    gmail = GmailService()
    logger.info(f"Fetching up to {request.max_emails_to_fetch} emails from Gmail...")
    gmail_emails = gmail.fetch_inbox_emails(max_results=request.max_emails_to_fetch)
    logger.info(f"Fetched {len(gmail_emails)} emails from Gmail")

    if not gmail_emails:
        logger.warning("No emails fetched")
        return {"fetched": 0, "message": "No emails fetched"}

    # Store in DB
    result = bulk_upsert_emails(gmail_emails, provider="gmail")
    stored_emails = get_all_emails()

    # Build structured JSON response
    emails_json = []
    for e in gmail_emails:
        emails_json.append({
            "id": str(e.get("id")),
            "from": e.get("from"),
            "to": e.get("to"),
            "subject": e.get("subject"),
            "snippet": clean_email_text(e.get("snippet", "")),
            "date": e.get("date"),
            "thread_id": e.get("thread_id"),
        })

    return {
        "fetched": len(gmail_emails),
        "upsert_result": result,
        "total_stored": len(stored_emails),
        "emails": emails_json
    }


# Classify unclassified emails
@app.post("/classify")
def classify_emails(limit: int = Query(5, description="Number of emails to classify")):
    classified = classify_unclassified_emails(limit=limit, delay=6)
    return {
        "status": "Classification completed",
        "classified_count": len(classified),
        "classified_emails": [{
            "from": email.get("from"),
            "subject": email.get("subject"),
            "category": email.get("category"),
            "snippet": clean_email_text(email.get("snippet", "")),
            "date": email.get("date"),
            "thread_id": email.get("thread_id"),
            "classification": {
                "category": email.get("category"),
                "confidence": email.get("confidence"),
                "reasoning": email.get("reasoning"),
                "summary": email.get("summary")
            }
        } for email in classified] if classified else []
    }

@app.post("/respond")
def respond_email(request: RespondRequest):
    try:
        result = generate_response(
            email_id=request.email_id,
            human_input=request.draft,
            send_email_flag=True
        )
        return {
            "status": result["status"],
            "email_id": result["email_id"],
            "to": result["to"],
            "from": result["from"],
            "subject": result["subject"],
            "draft": result["draft"],
            "gmail_response": result["gmail_response"],
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    
# Endpoint to get all classified emails
@app.get("/classified-emails")
def get_classified_emails():
    classified_emails = get_all_classified_emails()
    emails_json = []
    for email in classified_emails:
        emails_json.append({
            "id": str(email.get("id")),
            "from": email.get("from"),
            "to": email.get("to"),
            "subject": email.get("subject"),
            "snippet": clean_email_text(email.get("snippet", "")),
            "date": email.get("date"),
            "thread_id": email.get("thread_id"),
            "category": email.get("category"),
            "confidence": email.get("confidence"),
            "reasoning": email.get("reasoning"),
            "summary": email.get("summary"),
        })
    classified_emails = emails_json
        
    return {"classified_emails": classified_emails}

# Endpoint for getting all responded emails

@app.get("/responded-emails")
def get_responded_emails():
    from services.db_service import get_responded_emails
    responded_emails = get_responded_emails()
    emails_json = []
    for r in responded_emails:
        emails_json.append({
            "email_id": r.get("email_id"),
            "thread_id": r.get("thread_id"),
            "to": r.get("to"),
            "from": r.get("from"),
            "subject": r.get("subject"),
            "body": r.get("body"),
            "status": r.get("status"),
            "edited_by_human": r.get("edited_by_human"),
            "created_at": r.get("created_at"),
            "sent_at": r.get("sent_at"),
            "gmail_response": r.get("gmail_response"),
        })
    responded_emails = emails_json
    return {"responded_emails": responded_emails}
