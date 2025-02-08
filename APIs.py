# -*- coding: utf-8 -*-
"""
Power Consumption Management API System
Created on Sat Jan 18 10:32:54 2025

This module implements the core API functionality of the power consumption management system, including:
1. Account registration and management
2. Meter reading reception (every 30 minutes)
3. Power consumption queries
4. Bill queries

@author: Lenovo
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.responses import JSONResponse
import os
import pandas as pd

# Add response models
class AccountResponse(BaseModel):
    meter_id: str
    message: str = "Account successfully created"

class MeterReadingResponse(BaseModel):
    success: bool
    message: str

class ConsumptionResponse(BaseModel):
    consumption: float
    period: str
    meter_id: str

class ArchiveResponse(BaseModel):
    success: bool
    message: str
    period: str

class ElectricityAccount:
    """Electricity Account class for storing and managing individual user's power consumption data"""
    
    def __init__(self, meter_id: str, owner_name: str, address: str):
        self.meter_id = meter_id
        self.owner_name = owner_name
        self.address = address
        self.family_members = []  # Store family member information
        self.meter_readings = {}  # Store meter readings, format: {timestamp: reading}
        self.created_at = datetime.now()
    
    def calculate_consumption(self, start_time: datetime, end_time: datetime) -> float:
        """
        Calculate power consumption for a specified time period
        
        Args:
            start_time: Start time
            end_time: End time
            
        Returns:
            float: Power consumption during the time period (kWh)
        """
        # Get readings within the time range
        relevant_readings = {ts: reading for ts, reading in self.meter_readings.items() 
                           if start_time <= ts <= end_time}
        
        if not relevant_readings:
            raise ValueError("No meter readings found in the specified time period.")
        
        # Get first and last readings within the time period
        timestamps = sorted(relevant_readings.keys())
        if len(timestamps) < 2:
            raise ValueError("Not enough readings to calculate consumption. At least two readings are required.")
            
        first_reading = relevant_readings[timestamps[0]]
        last_reading = relevant_readings[timestamps[-1]]
        
        # Calculate consumption (last reading minus first reading)
        return last_reading - first_reading

class ElectricityManagementSystem:
    """Main Electricity Management System class implementing core API functionality"""
    
    def __init__(self):
        self.accounts: Dict[str, ElectricityAccount] = {}  # 使用meter_id作为key
        self.archived_readings: Dict[str, Dict[str, Dict[datetime, float]]] = {}  # Store archived readings
        
    def register_account(self, owner_name: str, address: str, meter_id: str) -> str:
        """
        Register new account
        
        Args:
            owner_name: Owner's name
            address: Residential address
            meter_id: Meter ID
            
        Returns:
            str: Meter ID
        """
        if meter_id in self.accounts:
            raise ValueError("Meter already registered")
            
        self.accounts[meter_id] = ElectricityAccount(meter_id, owner_name, address)
        return meter_id
    
    def record_meter_reading(self, meter_id: str, timestamp: datetime, reading: float) -> bool:
        """
        Record half-hourly meter reading
        
        Args:
            meter_id: Meter ID
            timestamp: Timestamp (must be on the hour, half-hour, or 23:59)
            reading: Meter reading (kWh)
            
        Returns:
            bool: Whether the data was successfully recorded
        """
        # Validate meter ID
        if meter_id not in self.accounts:
            return False
            
        # Validate timestamp is on the hour, half-hour, or 23:59
        valid_time = (
            (timestamp.minute == 0 and timestamp.second == 0) or  # On the hour
            (timestamp.minute == 30 and timestamp.second == 0) or  # Half-hour
            (timestamp.hour == 23 and timestamp.minute == 59 and timestamp.second == 0)  # 23:59
        )
        if not valid_time:
            return False
            
        # If data is for 23:59, normalize it to 00:00 of the next day
        if timestamp.hour == 23 and timestamp.minute == 59:
            timestamp = (timestamp + timedelta(minutes=1)).replace(second=0, microsecond=0)
            
        account = self.accounts[meter_id]
        
        # Validate reading is reasonable (new reading should be greater than all previous readings)
        previous_readings = {ts: r for ts, r in account.meter_readings.items() if ts < timestamp}
        if previous_readings and reading < max(previous_readings.values()):
            return False
            
        account.meter_readings[timestamp] = reading
        return True
    
    def get_consumption(self, meter_id: str, period: str) -> Optional[float]:
        """
        Query power consumption for specified period
        
        Args:
            meter_id: Meter ID
            period: Query period ('last_30min', 'today', 'this_week', 'this_month', 'last_month')
            
        Returns:
            float: Total power consumption
        """
        if meter_id not in self.accounts:
            return None
            
        account = self.accounts[meter_id]
        now = datetime.now()
        
        # Adjust current time to the nearest valid time point
        if now.minute > 30:
            now = now.replace(minute=30, second=0, microsecond=0)
        elif now.minute > 0:
            now = now.replace(minute=0, second=0, microsecond=0)
        else:
            now = now.replace(second=0, microsecond=0)
        
        if period == 'last_30min':
            start_time = now - timedelta(minutes=30)
            end_time = now
        elif period == 'today':
            start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_time = now
        elif period == 'this_week':
            start_time = now - timedelta(days=now.weekday())
            start_time = start_time.replace(hour=0, minute=0, second=0, microsecond=0)
            end_time = now
        elif period == 'this_month':
            start_time = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_time = now
        elif period == 'last_month':
            first_day_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            start_time = first_day_this_month - timedelta(days=1)
            start_time = start_time.replace(day=1)
            end_time = first_day_this_month
        else:
            return None
            
        return account.calculate_consumption(start_time, end_time)
    
    def get_last_month_bill(self, meter_id: str) -> Optional[float]:
        """
        Get last month's bill (kWh only)
        
        Args:
            meter_id: Meter ID
            
        Returns:
            float: Last month's total power consumption
        """
        return self.get_consumption(meter_id, 'last_month')

    def archive_readings(self, period: str, clear_memory: bool = False) -> bool:
        """
        Archive meter readings for specified period and prepare for new data
        
        Args:
            period: Archive period ('daily' or 'monthly')
            clear_memory: Whether to clear the archived data from memory after saving
            
        Returns:
            bool: Whether archiving was successful
        """
        try:
            now = datetime.now()
            
            if period not in ['daily', 'monthly']:
                return False
            
            # 创建存档目录
            archive_dir = os.path.join(os.getcwd(), "Archive")
            os.makedirs(archive_dir, exist_ok=True)
            
            # 准备所有数据
            all_readings = []
            
            # Archive data for each account
            for meter_id, account in self.accounts.items():
                # Get readings to archive
                if period == 'daily':
                    start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
                    archive_key = start_time.date().isoformat()
                    filename = f"daily_{archive_key}.csv"
                else:  # monthly
                    start_time = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                    archive_key = start_time.strftime('%Y-%m')
                    filename = f"monthly_{archive_key}.csv"
                
                # Filter readings for the current period
                period_readings = {
                    ts: reading for ts, reading in account.meter_readings.items()
                    if ts >= start_time
                }
                
                # 将数据添加到列表中（只包含必要字段）
                for timestamp, reading in period_readings.items():
                    all_readings.append({
                        'meter_id': meter_id,
                        'timestamp': timestamp,
                        'reading': reading
                    })
                
                if period_readings:
                    # 存储到归档数据结构中
                    if meter_id not in self.archived_readings:
                        self.archived_readings[meter_id] = {'daily': {}, 'monthly': {}}
                    self.archived_readings[meter_id][period][archive_key] = period_readings
                    
                    # 只有在 clear_memory 为 True 时才清除内存数据
                    if clear_memory:
                        for ts in period_readings.keys():
                            del account.meter_readings[ts]
            
            # 如果有数据要归档
            if all_readings:
                # 创建DataFrame并保存为CSV
                df = pd.DataFrame(all_readings)
                # 确保timestamp列以正确的格式输出
                df['timestamp'] = df['timestamp'].dt.strftime('%Y-%m-%dT%H:%M:%S')
                df = df.sort_values(['meter_id', 'timestamp'])
                csv_path = os.path.join(archive_dir, filename)
                df.to_csv(csv_path, index=False, encoding='utf-8')
                print(f"Archived data saved to {csv_path}")
                
            return True
            
        except Exception as e:
            print(f"Error during archiving: {str(e)}")
            return False

# Create FastAPI application
app = FastAPI(title="Power Consumption Management API System")
ems = ElectricityManagementSystem()

@app.post("/register_account", response_model=AccountResponse)
async def register_account(owner_name: str, region: str, meter_id: str):
    try:
        meter_id = ems.register_account(owner_name, region, meter_id)
        return AccountResponse(meter_id=meter_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/receive_meter_reading", response_model=MeterReadingResponse)
async def receive_meter_reading(meter_id: str, timestamp: datetime, reading: float):
    """
    接收电表读数
    
    参数:
    - meter_id: 电表ID
    - timestamp: 时间戳 (格式: YYYY-MM-DDTHH:mm:00, 必须是整点或半点)
    - reading: 读数值
    
    示例:
    ```
    /receive_meter_reading?meter_id=123-456-789&timestamp=2025-02-08T01:00:00&reading=100.5
    ```
    """
    # 验证时间戳是否在整点或半点
    if timestamp.minute not in [0, 30] or timestamp.second != 0:
        raise HTTPException(
            status_code=400, 
            detail="Timestamp must be on the hour (HH:00:00) or half hour (HH:30:00)"
        )
    
    success = ems.record_meter_reading(meter_id, timestamp, reading)
    return MeterReadingResponse(
        success=success,
        message="Reading recorded successfully" if success else "Failed to record reading"
    )

@app.get("/get_consumption", response_model=ConsumptionResponse)
async def get_consumption(meter_id: str, period: str):
    try:
        consumption = ems.get_consumption(meter_id, period)
        if consumption is None:
            raise HTTPException(status_code=404, detail="Meter not found or invalid period")
        return ConsumptionResponse(
            consumption=consumption,
            period=period,
            meter_id=meter_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/get_last_month_bill", response_model=ConsumptionResponse)
async def get_last_month_bill(meter_id: str):
    consumption = ems.get_last_month_bill(meter_id)
    if consumption is None:
        raise HTTPException(status_code=404, detail="Meter not found")
    return ConsumptionResponse(
        consumption=consumption,
        period="last_month",
        meter_id=meter_id
    )

@app.post("/archive_and_prepare", response_model=ArchiveResponse)
async def archive_and_prepare(period: str):
    if period not in ['daily', 'monthly']:
        raise HTTPException(status_code=400, detail="Invalid period. Must be 'daily' or 'monthly'")
    
    success = ems.archive_readings(period)
    return ArchiveResponse(
        success=success,
        message=f"Successfully archived {period} readings" if success else "Failed to archive readings",
        period=period
    )

if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)
