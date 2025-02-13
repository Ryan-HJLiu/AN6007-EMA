import logging
import os
from datetime import datetime

# 创建logs目录
logs_dir = os.path.join(os.getcwd(), 'logs')
os.makedirs(logs_dir, exist_ok=True)

# 获取当前日期作为文件名
current_date = datetime.now().strftime('%Y-%m-%d')
log_file = os.path.join(logs_dir, f'system_logs_{current_date}.log')

# 配置日志处理器
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(
    logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
)

# 配置logger
logger = logging.getLogger("PowerManagementSystem")
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)

# 防止日志重复
logger.propagate = False
