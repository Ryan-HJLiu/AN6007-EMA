# -*- coding: utf-8 -*-
"""
Monthly Billing Server

Created on Tue Jan 21 20:04:07 2025

Functions:
1. Archive last month's billing data to CSV file
2. Clear memory for the new month
"""

from datetime import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import os
from typing import Optional

class MaintenanceResponse(BaseModel):
    success: bool
    message: str
    timestamp: str
    archive_path: Optional[str] = None

# Create maintenance server application
maintenance_app = FastAPI(title="Power Consumption Monthly Billing Service")

class MonthlyMaintenanceServer:
    """Monthly maintenance service for archiving meter readings and initializing new month"""
    
    def __init__(self, main_api_url: str = "http://localhost:8000"):
        self.main_api_url = main_api_url
    
    async def archive_month_readings(self) -> tuple[bool, Optional[str]]:
        """
        Archive current month's meter readings to CSV
        
        Returns:
            tuple: (success status, archive file path if successful)
        """
        try:
            # 调用主API的归档endpoint
            response = requests.post(
                f"{self.main_api_url}/archive_and_prepare",
                params={"period": "monthly"}
            )
            
            if response.status_code == 200:
                # 获取当前月份作为文件名
                current_month = datetime.now().strftime('%Y-%m')
                expected_file = os.path.join(
                    os.getcwd(), 
                    "Archive", 
                    f"monthly_{current_month}.csv"
                )
                
                if os.path.exists(expected_file):
                    print(f"Archive completed: {response.json()['message']}")
                    print(f"Archive file saved at: {expected_file}")
                    return True, expected_file
                else:
                    print("Warning: Archive completed but file not found")
                    return True, None
            else:
                print(f"Archive failed: {response.json().get('detail', 'Unknown error')}")
                return False, None
                
        except Exception as e:
            print(f"Error during archive process: {str(e)}")
            return False, None

# Create maintenance server instance
monthly_server = MonthlyMaintenanceServer()

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
