# -*- coding: utf-8 -*-
"""
Data recovery module

Functionality:
1. Restore archived data from Archive directory (from month start to yesterday)
2. Restore unarchived data from today's log file
"""

import os
import csv
import re
from datetime import datetime
from typing import Dict, List, Tuple
from loggers import logger

class DataRestorer:
    """
    Class for restoring meter readings data from Archive and logs
    
    Functionality:
    1. Restore archived data from Archive directory (from month start to yesterday)
    2. Restore unarchived data from today's log file
    """
    
    def __init__(self):
        self.archive_dir = os.path.join(os.getcwd(), "Archive")
        self.logs_dir = os.path.join(os.getcwd(), "logs")
        
    def _get_daily_files_for_current_month(self) -> List[str]:
        """
        Get all daily CSV files for current month from Archive directory
        
        Returns:
        - List of file paths
        """
        now = datetime.now()
        year = now.year
        month = now.month
        
        archive_dir = os.path.join(self.archive_dir, f"{year:04d}", f"{month:02d}")
        if not os.path.exists(archive_dir):
            return []
        
        daily_files = []
        for file in os.listdir(archive_dir):
            if file.endswith(".csv"):
                daily_files.append(os.path.join(archive_dir, file))
        
        return daily_files
    
    def _parse_log_line(self, line: str) -> Tuple[str, datetime, float]:
        """
        Parse log line to extract meter reading record
        
        Parameters:
        - line: Log line to parse
        
        Returns:
        - Tuple of (meter_id, timestamp, reading)
        
        Example log line:
        INFO - 2024-02-13 03:05:00,123 - Meter reading successfully recorded for meter ID: 123-456-789, timestamp: 2024-02-13T03:00:00, reading: 100.5
        """
        # Extract meter ID, timestamp and reading using regex
        pattern = r"Meter reading successfully recorded for meter ID: ([\w-]+), timestamp: ([\d-]+T[\d:]+), reading: ([\d.]+)"
        match = re.search(pattern, line)
        if not match:
            return None
        
        meter_id = match.group(1)
        timestamp = datetime.fromisoformat(match.group(2))
        reading = float(match.group(3))
        
        return meter_id, timestamp, reading
    
    def _get_today_readings_from_logs(self) -> Dict[str, Dict[datetime, float]]:
        """
        Get today's meter readings from log file
        
        Returns:
        - Dictionary with meter IDs as keys and dictionaries of timestamp-reading pairs as values
        """
        today = datetime.now().date()
        log_file = os.path.join(self.logs_dir, f"{today.isoformat()}.log")
        if not os.path.exists(log_file):
            return {}
        
        readings = {}
        with open(log_file, "r") as f:
            for line in f:
                if "Meter reading successfully recorded" in line:
                    result = self._parse_log_line(line)
                    if result:
                        meter_id, timestamp, reading = result
                        if meter_id not in readings:
                            readings[meter_id] = {}
                        readings[meter_id][timestamp] = reading
        
        return readings
    
    def restore_data(self) -> Dict[str, Dict[datetime, float]]:
        """
        Restore meter readings data from Archive and logs
        
        Returns:
        - Dictionary with meter IDs as keys and dictionaries of timestamp-reading pairs as values
        """
        logger.info("Starting data restoration process")
        restored_data = {}
        
        # 1. Restore from daily CSV files
        daily_files = self._get_daily_files_for_current_month()
        for file in daily_files:
            with open(file, "r") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    meter_id = row["meter_id"]
                    timestamp = datetime.fromisoformat(row["timestamp"])
                    reading = float(row["reading"])
                    
                    if meter_id not in restored_data:
                        restored_data[meter_id] = {}
                    restored_data[meter_id][timestamp] = reading
        
        # 2. Restore from today's logs
        today_readings = self._get_today_readings_from_logs()
        for meter_id, readings in today_readings.items():
            if meter_id not in restored_data:
                restored_data[meter_id] = {}
            restored_data[meter_id].update(readings)
        
        logger.info(f"Restored {len(restored_data)} meter(s) data")
        return restored_data
