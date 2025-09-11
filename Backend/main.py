from services.gmail_service import GmailService
from utils.parser import clean_email_text
from services.db_service import bulk_upsert_emails, get_all_emails
from services.logger import get_logger

logger = get_logger(__name__)

def run():
    logger.info("Starting Smart Email Assistant Backend")

    # Terminal should show only important messages; detailed logs go to file
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

    # -----------------------------
    # Step 1: Initialize Gmail Service
    # -----------------------------
    gmail = GmailService()

    # -----------------------------
    # Step 2: Fetch Emails
    # -----------------------------
    max_emails_to_fetch = 5
    logger.info(f"Fetching up to {max_emails_to_fetch} emails from Gmail...")
    gmail_emails = gmail.fetch_inbox_emails(max_results=max_emails_to_fetch)
    logger.info(f"Fetched {len(gmail_emails)} emails from Gmail")
    print(f"{len(gmail_emails)} email fetched" if len(gmail_emails) == 1 else f"{len(gmail_emails)} emails fetched")

    if not gmail_emails:
        logger.warning("No emails fetched. Exiting.")
        return

    # -----------------------------
    # Step 3: Store Emails in MongoDB
    # -----------------------------
    logger.info("Storing fetched emails in MongoDB...")
    result = bulk_upsert_emails(gmail_emails, provider="gmail")
    logger.info(f"Upsert Results: {result}")
    print("stored in mongodb")

    # Step 4: Show the fetched emails in a structured table
    _print_table(gmail_emails)

    # -----------------------------
    # Optional: Retrieve Stored Emails from DB
    # -----------------------------
    stored_emails = get_all_emails()
    logger.info(f"Total stored emails in MongoDB: {len(stored_emails)}")
    print("done")

if __name__ == "__main__":
    run()