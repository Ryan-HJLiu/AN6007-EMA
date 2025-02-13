# -*- coding: utf-8 -*-
"""
Monthly Billing Server

Created on Tue Jan 21 20:04:07 2025

Functions:
1. Archive last month's billing data to CSV file
2. Clear memory for the new month
"""

from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import os
from typing import Optional, Dict
import csv
from loggers import logger

class MaintenanceResponse(BaseModel):
    success: bool
    message: str
    timestamp: str
    archive_path: Optional[str] = None

# Create maintenance server application
maintenance_app = FastAPI(title="Power Consumption Monthly Billing Service")

class MonthlyMaintenance:
    """
    Monthly maintenance class for archiving meter readings
    
    Functionality:
    1. Archive last month's meter readings to CSV files
    2. Clear archived data from memory
    """
    
    def __init__(self):
        self.archive_dir = os.path.join("Archive")
    
    def _get_last_month_readings(self, meter_readings: Dict[datetime, float]) -> Dict[datetime, float]:
        """
        Get last month's readings from meter readings
        
        Parameters:
        - meter_readings: Dictionary of timestamp-reading pairs
        
        Returns:
        - Dictionary of timestamp-reading pairs for last month
        """
        now = datetime.now()
        first_day_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_month = first_day_this_month - timedelta(days=1)
        month_start = last_month.replace(day=1)
        
        return {ts: reading for ts, reading in meter_readings.items() if month_start <= ts < first_day_this_month}
    
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
    
    def perform_maintenance(self, meter_id: str, meter_readings: Dict[datetime, float]) -> bool:
        """
        Perform monthly maintenance for a single meter
        
        Parameters:
        - meter_id: Meter ID
        - meter_readings: Dictionary of timestamp-reading pairs
        
        Returns:
        - Whether maintenance was successful
        """
        try:
            # Get last month's readings
            last_month_readings = self._get_last_month_readings(meter_readings)
            if last_month_readings:
                # Save to archive
                self._save_readings_to_csv(meter_id, last_month_readings)
                # Clear from memory
                for ts in last_month_readings.keys():
                    del meter_readings[ts]
            
            return True
            
        except Exception as e:
            logger.error(f"Error during monthly maintenance for meter {meter_id}: {str(e)}")
            return False

# Create maintenance server instance
monthly_server = MonthlyMaintenance()

@maintenance_app.post("/perform_monthly_maintenance", response_model=MaintenanceResponse)
async def perform_monthly_maintenance():
    """
    执行月度维护任务:
    1. 将当月的电表读数保存为CSV文件
    2. 清理内存中的当月数据
    
    CSV文件将保存在 ./Archive 目录下
    文件命名格式: monthly_YYYY-MM.csv
    """
    try:
        success, archive_path = await monthly_server.archive_month_readings()
        
        return MaintenanceResponse(
            success=success,
            message="Monthly maintenance completed" if success else "Error during maintenance",
            timestamp=datetime.now().isoformat(),
            archive_path=archive_path
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Maintenance process failed: {str(e)}"
        )
