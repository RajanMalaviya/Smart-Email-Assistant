import os
import datetime
from typing import List, Dict, Any
from email.utils import parsedate_to_datetime

from pymongo import MongoClient, UpdateOne
from pymongo.errors import ServerSelectionTimeoutError
from gridfs import GridFS
from pydantic import BaseModel, Field
from services.logger import get_logger
from config.settings import MONGO_URI as SETTINGS_MONGO_URI, MONGO_DB as SETTINGS_MONGO_DB, MONGO_COLLECTION as SETTINGS_MONGO_COLLECTION

# ----------------------------
# CONFIGURATION
# ----------------------------
# Use config.settings (loads .env) to support Atlas SRV URIs
MONGO_URI = SETTINGS_MONGO_URI
MONGO_DB = SETTINGS_MONGO_DB
MONGO_COLLECTION = SETTINGS_MONGO_COLLECTION

# ----------------------------
# LOGGER SETUP (file only)
# ----------------------------
import logging
if not os.path.exists("logs"):
    os.makedirs("logs")
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[logging.FileHandler("logs/app.log")]
)
logger = logging.getLogger(__name__)

# ----------------------------
# DATABASE CONNECTION
# ----------------------------
if not MONGO_URI:
    logger.error("❌ MONGO_URI is not set. Provide your MongoDB Atlas connection string in .env")
    raise ValueError("MONGO_URI environment variable is required")

def _mask_uri(uri: str) -> str:
    if "@" not in uri:
        return uri
    # Mask credentials between scheme and host
    if uri.startswith("mongodb+srv://"):
        return "mongodb+srv://***:***@" + uri.split("@", 1)[1]
    if uri.startswith("mongodb://"):
        return "mongodb://***:***@" + uri.split("@", 1)[1]
    return uri

try:
    logger.info(f"Connecting to MongoDB at {_mask_uri(MONGO_URI)} (db='{MONGO_DB}', collection='{MONGO_COLLECTION}')")
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    client.server_info()  # verify connection
    db = client[MONGO_DB]
    emails_collection = db[MONGO_COLLECTION]
    logger.info("Connected to MongoDB successfully")
    print("Mongodb connected")
except ServerSelectionTimeoutError as e:
    logger.error(
        "❌ Failed to connect to MongoDB. If using Atlas, verify: 1) correct username/password, 2) your IP is allowlisted, 3) cluster is running.",
        exc_info=True,
    )
    raise e

# Ensure indexes
emails_collection.create_index(
    [("provider", 1), ("provider_message_id", 1)],
    unique=True,
    name="provider_msgid_unique"
)
emails_collection.create_index("date", name="date_idx")
emails_collection.create_index("from", name="from_idx")
emails_collection.create_index("labels", name="labels_idx")
logger.info("MongoDB indexes ensured")

# ----------------------------
# EMAIL SCHEMA
# ----------------------------
class AttachmentModel(BaseModel):
    filename: str
    mimeType: str = None
    size: int = None
    attachmentId: str = None
    storage_id: str = None

class EmailModel(BaseModel):
    provider: str
    provider_message_id: str
    thread_id: str = None
    mailbox: str = None
    from_: str = Field(None, alias="from")
    to: List[str] = []
    cc: List[str] = []
    bcc: List[str] = []
    subject: str = ""
    snippet: str = ""
    body_plain: str = ""
    body_html: str = ""
    headers: Dict[str, str] = {}
    labels: List[str] = []
    attachments: List[AttachmentModel] = []
    date: datetime.datetime = None
    fetched_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    processed: bool = False
    classifications: Dict[str, Any] = {}
    metadata: Dict[str, Any] = {}

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {datetime.datetime: lambda v: v.isoformat()}

# ----------------------------
# HELPER FUNCTIONS
# ----------------------------
def _parse_date(value):
    if not value:
        return None
    if isinstance(value, datetime.datetime):
        return value
    try:
        return parsedate_to_datetime(value)
    except Exception:
        try:
            return datetime.datetime.fromisoformat(value)
        except Exception:
            return None

def _sanitize_email(raw: Dict[str, Any], provider: str) -> Dict[str, Any]:
    """Sanitize raw email from any provider into canonical DB format"""
    doc = {}
    doc['provider'] = provider
    doc['provider_message_id'] = raw.get('provider_message_id') or raw.get('id') or raw.get('messageId') or raw.get('message_id')
    doc['thread_id'] = raw.get('threadId') or raw.get('thread_id')
    doc['mailbox'] = raw.get('mailbox') or raw.get('mail_to') or raw.get('to')
    doc['from'] = raw.get('from') or raw.get('sender') or raw.get('from_email')
    doc['to'] = raw.get('to') if isinstance(raw.get('to'), list) else (raw.get('to_list') or ([raw.get('to')] if raw.get('to') else []))
    doc['cc'] = raw.get('cc') or []
    doc['bcc'] = raw.get('bcc') or []
    doc['subject'] = raw.get('subject') or raw.get('Subject') or ""
    doc['snippet'] = raw.get('snippet') or ""
    doc['body_plain'] = raw.get('body_plain') or raw.get('plain') or ""
    doc['body_html'] = raw.get('body_html') or raw.get('html') or ""
    doc['headers'] = raw.get('headers') or {}
    doc['labels'] = raw.get('labels') or raw.get('labelIds') or []
    doc['attachments'] = raw.get('attachments') or []
    parsed_date = _parse_date(raw.get('date') or (raw.get('internalDate') and int(raw.get('internalDate'))/1000 if raw.get('internalDate') else None))
    doc['date'] = parsed_date
    doc['fetched_at'] = datetime.datetime.utcnow()
    doc['processed'] = raw.get('processed', False)
    doc['classifications'] = raw.get('classifications', {})
    doc['metadata'] = raw.get('metadata', {})
    return doc

# ----------------------------
# CRUD OPERATIONS
# ----------------------------
def bulk_upsert_emails(raw_emails: List[Dict[str, Any]], provider: str = "gmail") -> Dict[str,int]:
    """Bulk upsert emails into MongoDB"""
    ops = []
    for raw in raw_emails:
        doc = _sanitize_email(raw, provider)
        if not doc.get('provider_message_id'):
            continue
        filter_q = {"provider": doc['provider'], "provider_message_id": doc['provider_message_id']}
        update = {"$set": doc, "$setOnInsert": {"created_at": datetime.datetime.utcnow()}}
        ops.append(UpdateOne(filter_q, update, upsert=True))

    if not ops:
        logger.warning("No valid emails to upsert")
        return {"upserted_count": 0, "modified_count": 0}

    result = emails_collection.bulk_write(ops, ordered=False)
    logger.info(f"Bulk upsert complete: Upserted {result.upserted_count}, Modified {result.modified_count}")
    return {"upserted_count": result.upserted_count, "modified_count": result.modified_count}

def store_attachment_gridfs(filename: str, data_bytes: bytes, content_type: str = None) -> str:
    """Store attachment in GridFS and return storage_id"""
    fs = GridFS(db)
    grid_id = fs.put(data_bytes, filename=filename, contentType=content_type)
    logger.debug(f"Stored attachment {filename} in GridFS with id {grid_id}")
    return str(grid_id)

def get_all_emails() -> List[Dict[str, Any]]:
    emails = list(emails_collection.find({}, {"_id": 0}))
    logger.info(f"Retrieved {len(emails)} emails from MongoDB")
    return emails
