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
        os.makedirs(self.archive_dir, exist_ok=True)
    
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
    
    def perform_maintenance(self, accounts: Dict[str, object]) -> bool:
        """
        Perform daily maintenance
        
        Parameters:
        - accounts: Dictionary of meter accounts
        
        Returns:
        - Whether maintenance was successful
        """
        try:
            # Get yesterday's date for file naming
            yesterday = (datetime.now() - timedelta(days=1)).date()
            archive_file = os.path.join(self.archive_dir, f"daily_{yesterday.isoformat()}.csv")
            
            # Collect all readings
            all_readings = []
            for meter_id, account in accounts.items():
                # Get yesterday's readings
                yesterday_readings = self._get_yesterday_readings(account.meter_readings)
                
                # Add to collection
                for ts, reading in yesterday_readings.items():
                    all_readings.append({
                        "meter_id": meter_id,
                        "timestamp": ts.isoformat(),
                        "reading": reading
                    })
                    
                    # Clear from memory
                    del account.meter_readings[ts]
            
            # Save to CSV if we have readings
            if all_readings:
                with open(archive_file, "w", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=["meter_id", "timestamp", "reading"])
                    writer.writeheader()
                    writer.writerows(all_readings)
                
                logger.info(f"Successfully archived {len(all_readings)} readings to {archive_file}")
            else:
                logger.info("No readings found for yesterday")
            
            return True
            
        except Exception as e:
            logger.error(f"Error during daily maintenance: {str(e)}")
            return False

# Create maintenance server instance
daily_server = DailyMaintenance()

@maintenance_app.post("/perform_daily_maintenance", response_model=MaintenanceResponse)
async def perform_daily_maintenance():
    """
    Perform daily maintenance tasks:
    1. Archive today's meter readings to CSV files
    2. Clear memory for the new day
    
    CSV files will be saved in the ./Archive directory
    File naming format: daily_YYYY-MM-DD.csv
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

