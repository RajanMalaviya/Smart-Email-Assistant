import logging
import os

# Create logs directory if not exists
if not os.path.exists("logs"):
    os.makedirs("logs")

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # DEBUG shows everything (INFO, WARNING, ERROR, CRITICAL)
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/app.log")  # log file only
    ]
)

# Get logger function
def get_logger(name: str):
    return logging.getLogger(name)