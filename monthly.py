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
        os.makedirs(self.archive_dir, exist_ok=True)
    
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
    
    def perform_maintenance(self, accounts: Dict[str, object]) -> bool:
        """
        Perform monthly maintenance
        
        Parameters:
        - accounts: Dictionary of meter accounts
        
        Returns:
        - Whether maintenance was successful
        """
        try:
            # Get last month's date for file naming
            now = datetime.now()
            if now.month == 1:
                year = now.year - 1
                month = 12
            else:
                year = now.year
                month = now.month - 1
            
            archive_file = os.path.join(self.archive_dir, f"monthly_{year:04d}-{month:02d}.csv")
            
            # Collect all readings
            all_readings = []
            for meter_id, account in accounts.items():
                # Get last month's readings
                last_month_readings = self._get_last_month_readings(account.meter_readings)
                
                # Add to collection
                for ts, reading in last_month_readings.items():
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
                logger.info("No readings found for last month")
            
            return True
            
        except Exception as e:
            logger.error(f"Error during monthly maintenance: {str(e)}")
            return False

# Create maintenance server instance
monthly_server = MonthlyMaintenance()

@maintenance_app.post("/perform_monthly_maintenance", response_model=MaintenanceResponse)
async def perform_monthly_maintenance():
    """
    Perform monthly maintenance tasks:
    1. Save current month's meter readings to CSV files
    2. Clear memory for the new month
    
    CSV files will be saved in the ./Archive directory
    File naming format: monthly_YYYY-MM.csv
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
