import os
from dotenv import load_dotenv
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB", "smart_email_db")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "emails")