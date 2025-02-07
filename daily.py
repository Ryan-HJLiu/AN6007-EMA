# -*- coding: utf-8 -*-
"""
Power Consumption Management - Daily Maintenance Program
Implementation:
1. Archive current day's meter readings
2. Initialize meter readings for the new day
"""

from datetime import datetime
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import asyncio
from typing import Optional

class MaintenanceResponse(BaseModel):
    success: bool
    message: str
    timestamp: str

# Create maintenance server application
maintenance_app = FastAPI(title="Power Consumption Management System Maintenance Service")

class DailyMaintenanceServer:
    """Daily maintenance service for archiving meter readings and initializing new day"""

    def __init__(self, main_api_url: str = "http://localhost:8000"):
        self.main_api_url = main_api_url

    async def archive_today_readings(self) -> bool:
        """
        Archive current day's meter readings
        
        Returns:
            bool: Whether archiving was successful
        """
        try:
            # Call the main API's archive endpoint
            response = requests.post(
                f"{self.main_api_url}/archive_and_prepare",
                params={"period": "daily"}
            )
            
            if response.status_code == 200:
                print(f"Archive completed: {response.json()['message']}")
                return True
            else:
                print(f"Archive failed: {response.json().get('detail', 'Unknown error')}")
                return False
                
        except Exception as e:
            print(f"Error during archive process: {str(e)}")
            return False

# Create maintenance server instance
daily_server = DailyMaintenanceServer()

@maintenance_app.post("/perform_daily_maintenance", response_model=MaintenanceResponse)
async def perform_daily_maintenance():
    """
    Perform daily maintenance tasks:
    1. Archive today's readings
    2. Prepare for receiving new day's readings
    """
    try:
        success = await daily_server.archive_today_readings()
        
        return MaintenanceResponse(
            success=success,
            message="Daily maintenance completed" if success else "Error during maintenance",
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Maintenance process failed: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    # Run maintenance server on a different port
    uvicorn.run(maintenance_app, host="localhost", port=8001)

# Trigger maintenance task via HTTP request:
# curl -X POST http://localhost:8001/perform_daily_maintenance