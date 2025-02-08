import logging
import os

logs_dir = os.path.join(os.getcwd(), 'logs')
os.makedirs(logs_dir, exist_ok=True)

logging.basicConfig(
    filename=os.path.join(logs_dir, 'system_logs.log'),
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("PowerManagementSystem")
