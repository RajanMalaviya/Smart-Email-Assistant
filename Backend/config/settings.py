import os
from dotenv import load_dotenv
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB", "smart_email_db")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "emails")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

CATEGORIES = [
    "Work / Professional",
    "Personal",
    "Support / Service Requests",
    "Promotions / Marketing",
    "Spam / Junk",
    "Finance / Bills",
    "Meetings / Scheduling",
    "Notifications / Updates"
]

#     """
# You are an intelligent email classification agent.

# Classify the given email into EXACTLY one of the following categories:
# {categories}

# Return your output as a JSON object with fields:
# - category: the chosen category
# - confidence: a number between 0 and 1 indicating confidence level

# Email Subject: {subject}
# Email Snippet: {snippet}
# Email Body: {body}
# """