import sys
from services.gmail_service import GmailService
from utils.parser import clean_email_text
from services.db_service import bulk_upsert_emails, get_all_emails
from services.logger import get_logger
from services.classifier import classify_unclassified_emails

logger = get_logger(__name__)

# Helper functions
def _truncate(text: str, max_len: int) -> str:
    if text is None:
        return ""
    text = str(text).replace("\n", " ").replace("\r", " ")
    return text if len(text) <= max_len else text[: max_len - 1] + "…"

def _print_table(rows):
    if not rows:
        return
    col_from = 28
    col_subject = 40
    col_snippet = 60
    header = f"{'From':<{col_from}} | {'Subject':<{col_subject}} | {'Snippet':<{col_snippet}}"
    separator = f"{'-'*col_from}-+-{'-'*col_subject}-+-{'-'*col_snippet}"
    print("\nGmail Emails:")
    print(header)
    print(separator)
    for row in rows:
        from_text = _truncate(row.get('from', 'Unknown'), col_from)
        subject_text = _truncate(row.get('subject', ''), col_subject)
        snippet_text = _truncate(clean_email_text(row.get('snippet', '')), col_snippet)
        print(f"{from_text:<{col_from}} | {subject_text:<{col_subject}} | {snippet_text:<{col_snippet}}")

# Fetch & Store Emails
def fetch_and_store_emails(max_emails_to_fetch: int = 10):
    gmail = GmailService()
    logger.info(f"Fetching up to {max_emails_to_fetch} emails from Gmail...")
    gmail_emails = gmail.fetch_inbox_emails(max_results=max_emails_to_fetch)
    logger.info(f"Fetched {len(gmail_emails)} emails from Gmail")
    print(f"{len(gmail_emails)} email fetched" if len(gmail_emails) == 1 else f"{len(gmail_emails)} emails fetched")

    if not gmail_emails:
        logger.warning("No emails fetched. Exiting.")
        return

    logger.info("Storing fetched emails in MongoDB...")
    result = bulk_upsert_emails(gmail_emails, provider="gmail")
    logger.info(f"Upsert Results: {result}")
    print("stored in mongodb")

    _print_table(gmail_emails)

    stored_emails = get_all_emails()
    logger.info(f"Total stored emails in MongoDB: {len(stored_emails)}")
    print("done")

# Main Runner
if __name__ == "__main__":
    task = sys.argv[1] if len(sys.argv) > 1 else "all"

    if task == "fetch":
        print("📥 Running fetch mode...")
        fetch_and_store_emails(max_emails_to_fetch=10)

    elif task == "classify":
        print("🔎 Running classifier mode...")
        classify_unclassified_emails()

    elif task == "all":
        print("📥 Running fetch + classify mode...")
        fetch_and_store_emails(max_emails_to_fetch=10)
        print("\n🚀 Starting email classifier...")
        classify_unclassified_emails()

    else:
        print(f"⚠️ Unknown task: {task}")
        print("Usage: python main.py [fetch|classify|all]")