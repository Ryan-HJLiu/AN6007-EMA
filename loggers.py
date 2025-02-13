import os
import logging
from datetime import datetime

# Create logs directory if not exists
os.makedirs("logs", exist_ok=True)

# Configure logger
logger = logging.getLogger("power_consumption")
logger.setLevel(logging.INFO)

# Create file handler
today = datetime.now().date()
log_file = os.path.join("logs", f"{today.isoformat()}.log")
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.INFO)

# Create console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Create formatter
formatter = logging.Formatter('%(levelname)s - %(asctime)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Add handlers to logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)
