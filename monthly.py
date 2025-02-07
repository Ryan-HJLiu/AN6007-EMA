# -*- coding: utf-8 -*-
"""
Monthly Billing Server

Created on Tue Jan 21 20:04:07 2025

Functions:
1. Archive last month's billing data (using get_last_month_bill)
2. Calculate current month's power consumption (using get_consumption)
"""

from datetime import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
from typing import List, Optional

class BillingResponse(BaseModel):
    success: bool
    message: str
    timestamp: str
    current_month_consumption: Optional[float] = None
    last_month_consumption: Optional[float] = None

class MonthlyBillingServer:
    """Monthly Billing Server"""
    
    def __init__(self, main_api_url: str = "http://localhost:8000"):
        self.main_api_url = main_api_url
    
    async def archive_last_month_billing(self) -> bool:
        """
        Archive last month's billing data
        
        Returns:
            bool: Whether archiving was successful
        """
        try:
            # Call the main API's archive endpoint
            response = requests.post(
                f"{self.main_api_url}/archive_and_prepare",
                params={"period": "monthly"}
            )
            
            if response.status_code == 200:
                print(f"Monthly billing archive completed: {response.json()['message']}")
                return True
            else:
                print(f"Monthly billing archive failed: {response.json().get('detail', 'Unknown error')}")
                return False
                
        except Exception as e:
            print(f"Error during monthly billing archive: {str(e)}")
            return False
    
    async def get_current_month_consumption(self, account_id: str) -> Optional[float]:
        """Get current month's power consumption"""
        try:
            response = requests.get(
                f"{self.main_api_url}/get_consumption",
                params={
                    "account_id": account_id,
                    "period": "this_month"
                }
            )
            
            if response.status_code == 200:
                return response.json()["consumption"]
            return None
            
        except Exception as e:
            print(f"Failed to get current month consumption: {str(e)}")
            return None
    
    async def get_last_month_consumption(self, account_id: str) -> Optional[float]:
        """Get last month's power consumption"""
        try:
            response = requests.get(
                f"{self.main_api_url}/get_last_month_bill",
                params={"account_id": account_id}
            )
            
            if response.status_code == 200:
                return response.json()["consumption"]
            return None
            
        except Exception as e:
            print(f"Failed to get last month consumption: {str(e)}")
            return None

# Create FastAPI application
billing_app = FastAPI(title="Power Consumption Monthly Billing Service")
billing_server = MonthlyBillingServer()

@billing_app.post("/perform_monthly_maintenance", response_model=BillingResponse)
async def perform_monthly_maintenance(account_id: str):
    """
    Perform monthly maintenance tasks:
    1. Archive last month's billing
    2. Calculate current month's consumption
    """
    try:
        # Archive last month's data
        archive_success = await billing_server.archive_last_month_billing()
        
        # Get current and last month's consumption
        current_month = await billing_server.get_current_month_consumption(account_id)
        last_month = await billing_server.get_last_month_consumption(account_id)
        
        return BillingResponse(
            success=archive_success,
            message="Monthly maintenance completed" if archive_success else "Error during maintenance",
            timestamp=datetime.now().isoformat(),
            current_month_consumption=current_month,
            last_month_consumption=last_month
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Monthly maintenance failed: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    # Run billing server on a different port
    uvicorn.run(billing_app, host="localhost", port=8002)

# Trigger monthly maintenance task via HTTP request:
# curl -X POST "http://localhost:8002/perform_monthly_maintenance?account_id=ACC_1"