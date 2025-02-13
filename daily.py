# -*- coding: utf-8 -*-
"""
Power Consumption Management - Daily Maintenance Program
Implementation:
1. Archive current day's meter readings to CSV file
2. Clear memory for the new day
"""

from datetime import datetime, timedelta
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import asyncio
from typing import Optional, Dict, List
from loggers import logger
import csv

class MaintenanceResponse(BaseModel):
    success: bool
    message: str
    timestamp: str
    archive_path: Optional[str] = None

# Create maintenance server application
maintenance_app = FastAPI(title="Power Consumption Management System Maintenance Service")

class DailyMaintenance:
    """
    Daily maintenance class for archiving meter readings
    
    Functionality:
    1. Archive yesterday's meter readings to CSV files
    2. Clear archived data from memory
    """
    
    def __init__(self):
        self.archive_dir = os.path.join("Archive")
    
    def _get_yesterday_readings(self, meter_readings: Dict[datetime, float]) -> Dict[datetime, float]:
        """
        Get yesterday's readings from meter readings
        
        Parameters:
        - meter_readings: Dictionary of timestamp-reading pairs
        
        Returns:
        - Dictionary of timestamp-reading pairs for yesterday
        """
        yesterday = (datetime.now() - timedelta(days=1)).date()
        day_start = datetime.combine(yesterday, datetime.min.time())
        day_end = day_start + timedelta(days=1)
        
        return {ts: reading for ts, reading in meter_readings.items() if day_start <= ts < day_end}
    
    def _create_archive_directory(self, year: int, month: int) -> None:
        """
        Create archive directory structure if not exists
        
        Parameters:
        - year: Year
        - month: Month
        """
        archive_path = os.path.join(self.archive_dir, f"{year:04d}", f"{month:02d}")
        os.makedirs(archive_path, exist_ok=True)
    
    def _save_readings_to_csv(self, meter_id: str, readings: Dict[datetime, float]) -> None:
        """
        Save readings to CSV file
        
        Parameters:
        - meter_id: Meter ID
        - readings: Dictionary of timestamp-reading pairs
        """
        if not readings:
            return
        
        # Get first timestamp to determine year and month
        first_ts = min(readings.keys())
        year = first_ts.year
        month = first_ts.month
        
        # Create directory structure
        self._create_archive_directory(year, month)
        
        # Save to CSV
        archive_path = os.path.join(self.archive_dir, f"{year:04d}", f"{month:02d}", f"{meter_id}.csv")
        
        # Check if file exists and get existing readings
        existing_readings = {}
        if os.path.exists(archive_path):
            with open(archive_path, "r") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    ts = datetime.fromisoformat(row["timestamp"])
                    reading = float(row["reading"])
                    existing_readings[ts] = reading
        
        # Merge with new readings
        all_readings = {**existing_readings, **readings}
        
        # Write all readings to CSV
        with open(archive_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["timestamp", "reading"])
            writer.writeheader()
            for ts in sorted(all_readings.keys()):
                writer.writerow({
                    "timestamp": ts.isoformat(),
                    "reading": all_readings[ts]
                })
    
    def perform_maintenance(self, accounts: Dict[str, object]) -> bool:
        """
        Perform daily maintenance
        
        Parameters:
        - accounts: Dictionary of meter accounts
        
        Returns:
        - Whether maintenance was successful
        """
        try:
            for meter_id, account in accounts.items():
                # Get yesterday's readings
                yesterday_readings = self._get_yesterday_readings(account.meter_readings)
                if yesterday_readings:
                    # Save to archive
                    self._save_readings_to_csv(meter_id, yesterday_readings)
                    # Clear from memory
                    for ts in yesterday_readings.keys():
                        del account.meter_readings[ts]
            
            return True
            
        except Exception as e:
            logger.error(f"Error during daily maintenance: {str(e)}")
            return False

# Create maintenance server instance
daily_server = DailyMaintenance()

@maintenance_app.post("/perform_daily_maintenance", response_model=MaintenanceResponse)
async def perform_daily_maintenance():
    """
    执行每日维护任务:
    1. 将当日的电表读数保存为CSV文件
    2. 清理内存中的当日数据
    
    CSV文件将保存在 ./Archive 目录下
    文件命名格式: daily_YYYY-MM-DD.csv
    """
    try:
        success, archive_path = await daily_server.archive_today_readings()
        
        return MaintenanceResponse(
            success=success,
            message="Daily maintenance completed" if success else "Error during maintenance",
            timestamp=datetime.now().isoformat(),
            archive_path=archive_path
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Maintenance process failed: {str(e)}"
        )

