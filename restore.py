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
        
        # Get all daily files in Archive directory
        daily_files = []
        for file in os.listdir(self.archive_dir):
            if file.startswith("daily_") and file.endswith(".csv"):
                # Extract date from filename
                try:
                    date_str = file[6:-4]  # Remove 'daily_' prefix and '.csv' suffix
                    file_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                    # Check if file is from current month
                    if file_date.year == year and file_date.month == month:
                        daily_files.append(os.path.join(self.archive_dir, file))
                except ValueError:
                    continue
        
        return sorted(daily_files)  # Sort files by date
    
    def _parse_log_line(self, line: str) -> Tuple[str, datetime, float]:
        """
        Parse log line to extract meter reading record
        
        Parameters:
        - line: Log line to parse
        
        Returns:
        - Tuple of (meter_id, timestamp, reading) or None if parsing fails
        
        Example log line:
        INFO - 2025-02-14 12:38:43,081 - Meter reading recorded successfully: 999-999-999, 2025-01-08 01:00:00, 100.5
        """
        try:
            # More strict regex pattern
            pattern = r"INFO - (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - Meter reading recorded successfully: ([\w-]+), (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}), ([\d.]+)"
            match = re.search(pattern, line)
            if not match:
                return None
            
            # Extract components
            log_timestamp = datetime.strptime(match.group(1).split(',')[0], "%Y-%m-%d %H:%M:%S")
            meter_id = match.group(2)
            reading_timestamp = datetime.strptime(match.group(3), "%Y-%m-%d %H:%M:%S")
            reading = float(match.group(4))
            
            # Validate reading timestamp
            if reading_timestamp.minute not in [0, 30] or reading_timestamp.second != 0:
                logger.warning(f"Invalid reading timestamp format in log: {reading_timestamp}")
                return None
            
            return meter_id, reading_timestamp, reading
        except (ValueError, IndexError) as e:
            logger.warning(f"Error parsing log line: {str(e)}")
            return None
    
    def _validate_reading(self, meter_id: str, timestamp: datetime, reading: float, readings: Dict[str, Dict[datetime, float]]) -> bool:
        """
        Validate reading before restoring
        
        Parameters:
        - meter_id: Meter ID
        - timestamp: Reading timestamp
        - reading: Reading value
        - readings: Current restored readings
        
        Returns:
        - Whether the reading is valid
        """
        try:
            # Check timestamp format
            if timestamp.minute not in [0, 30] or timestamp.second != 0:
                logger.warning(f"Invalid timestamp format: {timestamp}")
                return False
            
            # Check if reading already exists
            if meter_id in readings and timestamp in readings[meter_id]:
                existing_reading = readings[meter_id][timestamp]
                if abs(existing_reading - reading) > 0.01:  # Allow small floating point differences
                    logger.warning(f"Conflicting reading found for {meter_id} at {timestamp}: {existing_reading} != {reading}")
                    return False
                return False  # Skip duplicate reading
            
            return True
        except Exception as e:
            logger.warning(f"Error validating reading: {str(e)}")
            return False
    
    def _get_today_readings_from_logs(self) -> Dict[str, Dict[datetime, float]]:
        """
        Get today's meter readings from log file
        
        Returns:
        - Dictionary with meter IDs as keys and dictionaries of timestamp-reading pairs as values
        """
        today = datetime.now().date()
        log_file = os.path.join(self.logs_dir, f"{today.isoformat()}.log")
        if not os.path.exists(log_file):
            logger.warning(f"Today's log file not found: {log_file}")
            return {}
        
        readings = {}
        try:
            with open(log_file, "r", encoding='utf-8') as f:
                for line in f:
                    if "Meter reading recorded successfully" in line:
                        result = self._parse_log_line(line)
                        if result:
                            meter_id, timestamp, reading = result
                            if meter_id not in readings:
                                readings[meter_id] = {}
                            readings[meter_id][timestamp] = reading
                            logger.info(f"Restored reading from logs: {meter_id}, {timestamp}, {reading}")
        except Exception as e:
            logger.error(f"Error reading log file {log_file}: {str(e)}")
            return {}
        
        logger.info(f"Restored {sum(len(r) for r in readings.values())} readings from today's logs")
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
        restored_from_csv = 0
        for file in daily_files:
            try:
                with open(file, "r") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        meter_id = row["meter_id"]
                        timestamp = datetime.fromisoformat(row["timestamp"])
                        reading = float(row["reading"])
                        
                        if self._validate_reading(meter_id, timestamp, reading, restored_data):
                            if meter_id not in restored_data:
                                restored_data[meter_id] = {}
                            restored_data[meter_id][timestamp] = reading
                            restored_from_csv += 1
            except Exception as e:
                logger.error(f"Error processing CSV file {file}: {str(e)}")
                continue
        
        logger.info(f"Restored {restored_from_csv} readings from CSV files")
        
        # 2. Restore from today's logs
        today_readings = self._get_today_readings_from_logs()
        restored_from_logs = 0
        for meter_id, readings in today_readings.items():
            if meter_id not in restored_data:
                restored_data[meter_id] = {}
            for timestamp, reading in readings.items():
                if self._validate_reading(meter_id, timestamp, reading, restored_data):
                    restored_data[meter_id][timestamp] = reading
                    restored_from_logs += 1
        
        logger.info(f"Restored {restored_from_logs} readings from today's logs")
        logger.info(f"Total restored: {len(restored_data)} meter(s), {restored_from_csv + restored_from_logs} readings")
        return restored_data
