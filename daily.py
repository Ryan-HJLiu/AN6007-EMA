# -*- coding: utf-8 -*-
"""
Power Consumption Management - Daily Maintenance Program
Implementation:
1. Archive current day's meter readings to CSV file
2. Clear memory for the new day
"""

from datetime import datetime
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import asyncio
from typing import Optional
from loggers import logger

class MaintenanceResponse(BaseModel):
    success: bool
    message: str
    timestamp: str
    archive_path: Optional[str] = None

# Create maintenance server application
maintenance_app = FastAPI(title="Power Consumption Management System Maintenance Service")

class DailyMaintenanceServer:
    """Daily maintenance service for archiving meter readings and initializing new day"""

    def __init__(self, main_api_url: str = "http://localhost:8000"):
        self.main_api_url = main_api_url

    async def archive_today_readings(self) -> tuple[bool, Optional[str]]:
        """
        Archive current day's meter readings to CSV
        
        Returns:
            tuple: (success status, archive file path if successful)
        """
        logger.info("Starting daily archive process")
        try:
            response = requests.post(
                f"{self.main_api_url}/archive_and_prepare",
                params={"period": "daily"}
            )

            if response.status_code == 200:
                today = datetime.now().date().isoformat()
                expected_file = os.path.join(os.getcwd(), "Archive", f"daily_{today}.csv")

                if os.path.exists(expected_file):
                    logger.info(f"Daily archive completed successfully. File saved at: {expected_file}")
                    return True, expected_file
                else:
                    logger.warning("Daily archive completed, but file not found.")
                    return True, None
            else:
                logger.error(f"Daily archive failed. Response: {response.json().get('detail', 'Unknown error')}")
                return False, None

        except Exception as e:
            logger.exception(f"Exception during daily archive process: {str(e)}")
            return False, None

# Create maintenance server instance
daily_server = DailyMaintenanceServer()

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

