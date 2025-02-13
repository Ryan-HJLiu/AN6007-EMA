# -*- coding: utf-8 -*-
"""
数据恢复模块

功能：
1. 从Archive目录中恢复本月已归档的数据
2. 从当天的日志文件中恢复未归档的数据
"""

import os
import pandas as pd
from datetime import datetime, timedelta
import re
from typing import Dict, List, Tuple
from loggers import logger

class DataRestorer:
    def __init__(self):
        self.archive_dir = os.path.join(os.getcwd(), "Archive")
        self.logs_dir = os.path.join(os.getcwd(), "logs")
        
    def _get_daily_files_for_current_month(self) -> List[str]:
        """获取本月所有daily_*.csv文件"""
        now = datetime.now()
        first_day = now.replace(day=1)
        yesterday = now.date() - timedelta(days=1)
        
        daily_files = []
        current_date = first_day.date()
        
        while current_date <= yesterday:
            file_name = f"daily_{current_date.isoformat()}.csv"
            file_path = os.path.join(self.archive_dir, file_name)
            if os.path.exists(file_path):
                daily_files.append(file_path)
            current_date += timedelta(days=1)
            
        return daily_files
    
    def _parse_log_line(self, line: str) -> Tuple[bool, Dict]:
        """解析日志行，提取成功的meter reading记录"""
        # 匹配成功记录的meter reading的日志
        success_pattern = r"Recording meter reading: meter_id=([^,]+), timestamp=([^,]+), reading=([^\s]+)"
        match = re.search(success_pattern, line)
        
        if match and "successfully recorded" in line:
            meter_id = match.group(1)
            timestamp = datetime.fromisoformat(match.group(2))
            reading = float(match.group(3))
            return True, {
                "meter_id": meter_id,
                "timestamp": timestamp,
                "reading": reading
            }
        return False, {}
    
    def _get_today_readings_from_logs(self) -> List[Dict]:
        """从今天的日志文件中提取meter readings"""
        today = datetime.now().strftime('%Y-%m-%d')
        log_file = os.path.join(self.logs_dir, f"system_logs_{today}.log")
        
        if not os.path.exists(log_file):
            logger.warning(f"Today's log file not found: {log_file}")
            return []
        
        readings = []
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    success, reading_data = self._parse_log_line(line)
                    if success:
                        readings.append(reading_data)
        except Exception as e:
            logger.error(f"Error reading log file: {str(e)}")
            
        return readings
    
    def restore_data(self) -> Dict[str, Dict[datetime, float]]:
        """
        恢复本月的meter readings数据
        
        Returns:
            Dict[str, Dict[datetime, float]]: 恢复的数据，格式为 {meter_id: {timestamp: reading}}
        """
        logger.info("Starting data restoration process")
        restored_data: Dict[str, Dict[datetime, float]] = {}
        
        # 1. 从Archive恢复本月已归档的数据
        daily_files = self._get_daily_files_for_current_month()
        for file_path in daily_files:
            try:
                df = pd.read_csv(file_path)
                for _, row in df.iterrows():
                    meter_id = row['meter_id']
                    timestamp = datetime.fromisoformat(row['timestamp'])
                    reading = float(row['reading'])
                    
                    if meter_id not in restored_data:
                        restored_data[meter_id] = {}
                    restored_data[meter_id][timestamp] = reading
                    
                logger.info(f"Restored data from {file_path}")
            except Exception as e:
                logger.error(f"Error restoring data from {file_path}: {str(e)}")
                
        # 2. 从今天的日志恢复未归档的数据
        today_readings = self._get_today_readings_from_logs()
        for reading in today_readings:
            meter_id = reading['meter_id']
            timestamp = reading['timestamp']
            reading_value = reading['reading']
            
            if meter_id not in restored_data:
                restored_data[meter_id] = {}
            restored_data[meter_id][timestamp] = reading_value
            
        logger.info(f"Restored {len(restored_data)} meter(s) data")
        return restored_data
