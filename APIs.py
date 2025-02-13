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

import os
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.responses import JSONResponse
from loggers import logger
import csv

# Add response models
class AccountResponse(BaseModel):
    meter_id: str
    message: str = "Account successfully created"

class MeterReadingResponse(BaseModel):
    success: bool
    message: str

class ConsumptionResponse(BaseModel):
    meter_id: str
    period: str
    start_reading: float
    end_reading: float
    consumption: float
    start_time: str
    end_time: str

class BillingDetailsResponse(BaseModel):
    meter_id: str
    period: str
    start_reading: float
    end_reading: float
    consumption: float
    start_time: str
    end_time: str
    success: bool = True
    message: str = "Bill details retrieved successfully"

class ArchiveResponse(BaseModel):
    success: bool
    message: str
    period: str

class Account:
    """
    Account class for storing meter information and readings
    
    Attributes:
    - owner_name: Owner name
    - address: Address
    - meter_id: Meter ID
    - meter_readings: Dictionary storing meter readings, key is timestamp, value is reading
    """
    def __init__(self, owner_name: str, address: str, meter_id: str):
        self.owner_name = owner_name
        self.address = address
        self.meter_id = meter_id
        self.meter_readings: Dict[datetime, float] = {}

class APIs:
    """
    Main API class for system functionality
    
    Attributes:
    - accounts: Dictionary storing accounts, key is meter ID, value is Account object
    - is_receiving_data: Whether system is receiving data
    """
    def __init__(self):
        self.accounts: Dict[str, Account] = {}
        self.is_receiving_data = True
        self._load_accounts()
    
    def _load_accounts(self):
        """Load existing accounts from account.csv"""
        if not os.path.exists("account.csv"):
            # Create account.csv with headers if it doesn't exist
            with open("account.csv", "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["owner_name", "address", "meter_id"])
                writer.writeheader()
            return
        
        try:
            with open("account.csv", "r") as f:
                reader = csv.DictReader(f)
                if not reader.fieldnames or set(reader.fieldnames) != {"owner_name", "address", "meter_id"}:
                    logger.error("Invalid CSV headers in account.csv")
                    return
                
                for row in reader:
                    try:
                        account = Account(
                            owner_name=row["owner_name"],
                            address=row["address"],
                            meter_id=row["meter_id"]
                        )
                        self.accounts[account.meter_id] = account
                    except KeyError as e:
                        logger.error(f"Missing field in account.csv: {str(e)}")
                    except Exception as e:
                        logger.error(f"Error processing account row: {str(e)}")
        except Exception as e:
            logger.error(f"Error loading accounts: {str(e)}")
    
    def _save_accounts(self):
        """Save accounts to account.csv"""
        try:
            with open("account.csv", "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["owner_name", "address", "meter_id"])
                writer.writeheader()
                for account in self.accounts.values():
                    writer.writerow({
                        "owner_name": account.owner_name,
                        "address": account.address,
                        "meter_id": account.meter_id
                    })
            logger.info("Accounts saved successfully")
        except Exception as e:
            logger.error(f"Error saving accounts: {str(e)}")
            raise
    
    def register_account(self, owner_name: str, address: str, meter_id: str) -> str:
        """
        Register new account and save to account.csv
        
        Parameters:
        - owner_name: Owner name
        - address: Address
        - meter_id: Meter ID
        
        Returns:
        - meter_id: Registered meter ID
        
        Raises:
        - ValueError: If meter ID already exists
        """
        if meter_id in self.accounts:
            raise ValueError(f"Meter ID {meter_id} already exists")
        
        account = Account(owner_name, address, meter_id)
        self.accounts[meter_id] = account
        self._save_accounts()
        logger.info(f"Account registered successfully: {meter_id}")
        
        return meter_id
    
    def record_meter_reading(self, meter_id: str, timestamp: datetime, reading: float) -> bool:
        """
        Record meter reading
        
        Parameters:
        - meter_id: Meter ID
        - timestamp: Reading timestamp
        - reading: Reading value
        
        Returns:
        - bool: Whether recording was successful
        
        Raises:
        - ValueError: If meter ID not found or timestamp invalid
        """
        if not self.is_receiving_data:
            return False
        
        if meter_id not in self.accounts:
            raise ValueError(f"Meter ID {meter_id} not found")
        
        # Validate timestamp is on the hour or half hour
        if timestamp.minute not in [0, 30] or timestamp.second != 0:
            raise ValueError("Timestamp must be on the hour or half hour")
        
        # Record reading
        self.accounts[meter_id].meter_readings[timestamp] = reading
        logger.info(f"Meter reading recorded successfully: {meter_id}, {timestamp}, {reading}")
        return True
    
    def get_consumption(self, meter_id: str, period: str) -> Dict:
        """
        Get power consumption for specified period
        
        Parameters:
        - meter_id: Meter ID
        - period: Query period ('last_30min', 'today', 'this_week', 'this_month', 'last_month')
        
        Returns:
        Dictionary containing:
        - start_reading: First reading (kWh)
        - end_reading: Last reading (kWh)
        - consumption: Power consumption (kWh)
        - start_time: First reading timestamp
        - end_time: Last reading timestamp
        
        Raises:
        - ValueError: If meter ID not found, invalid period, or insufficient data
        """
        if meter_id not in self.accounts:
            raise ValueError(f"Meter ID {meter_id} not found")
        
        readings = self.accounts[meter_id].meter_readings
        if not readings:
            raise ValueError("No readings found for this meter")
        
        now = datetime.now()
        
        # Calculate time range based on period
        if period == "last_30min":
            end_time = now.replace(minute=30 if now.minute >= 30 else 0, second=0, microsecond=0)
            if now.minute >= 30:
                end_time = end_time.replace(hour=now.hour)
            else:
                end_time = end_time.replace(hour=now.hour-1 if now.hour > 0 else 23)
            start_time = end_time - timedelta(minutes=30)
        
        elif period == "today":
            start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_time = now
        
        elif period == "this_week":
            start_time = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
            end_time = now
        
        elif period == "this_month":
            start_time = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_time = now
        
        elif period == "last_month":
            # Get first day of current month
            first_day = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            # Get last day of previous month
            end_time = first_day - timedelta(days=1)
            # Get first day of previous month
            start_time = end_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        else:
            raise ValueError("Invalid period")
        
        # Filter readings within time range
        period_readings = {ts: reading for ts, reading in readings.items() if start_time <= ts <= end_time}
        
        if not period_readings:
            raise ValueError(f"No readings found for period {period}")
        
        if len(period_readings) < 2:
            raise ValueError(f"Insufficient readings for period {period}")
        
        # Get first and last readings
        sorted_times = sorted(period_readings.keys())
        start_reading = period_readings[sorted_times[0]]
        end_reading = period_readings[sorted_times[-1]]
        
        return {
            "start_reading": start_reading,
            "end_reading": end_reading,
            "consumption": end_reading - start_reading,
            "start_time": sorted_times[0].isoformat(),
            "end_time": sorted_times[-1].isoformat()
        }
    
    def get_last_month_bill(self, meter_id: str) -> Optional[Dict]:
        """
        Get last month's bill details
        
        Parameters:
        - meter_id: Meter ID
        
        Returns:
        Dictionary containing:
        - period: Billing period (YYYY-MM)
        - start_reading: First reading of the month (kWh)
        - end_reading: Last reading of the month (kWh)
        - consumption: Total power consumption (kWh)
        - start_time: First reading timestamp
        - end_time: Last reading timestamp
        
        Returns None if meter ID not found
        """
        if meter_id not in self.accounts:
            return None
        
        # Get last month's archive file path
        now = datetime.now()
        if now.month == 1:
            year = now.year - 1
            month = 12
        else:
            year = now.year
            month = now.month - 1
        
        archive_file = os.path.join("Archive", f"monthly_{year:04d}-{month:02d}.csv")
        
        if not os.path.exists(archive_file):
            raise FileNotFoundError(f"Archive file not found: monthly_{year:04d}-{month:02d}.csv")
        
        # Read archive file
        readings = {}
        try:
            with open(archive_file, "r") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row["meter_id"] == meter_id:  # Only process rows for this meter
                        timestamp = datetime.fromisoformat(row["timestamp"])
                        reading = float(row["reading"])
                        readings[timestamp] = reading
            
            if not readings:
                raise ValueError(f"No readings found for meter {meter_id} in monthly_{year:04d}-{month:02d}.csv")
            
            # Get first and last readings
            sorted_times = sorted(readings.keys())
            start_reading = readings[sorted_times[0]]
            end_reading = readings[sorted_times[-1]]
            
            return {
                "period": f"{year:04d}-{month:02d}",
                "start_reading": start_reading,
                "end_reading": end_reading,
                "consumption": end_reading - start_reading,
                "start_time": sorted_times[0].isoformat(),
                "end_time": sorted_times[-1].isoformat()
            }
        except Exception as e:
            logger.error(f"Error reading archive file: {str(e)}")
            raise
    
    def shutdown_system(self):
        """Stop system data reception"""
        self.is_receiving_data = False
        logger.info("System data reception stopped")
    
    def resume_system(self):
        """Resume system data reception"""
        self.is_receiving_data = True
        logger.info("System data reception resumed")

    def archive_readings(self, period: str, clear_memory: bool = False) -> bool:
        """
        Archive meter readings for specified period
        
        Parameters:
        - period: Archive period ('daily' or 'monthly')
        - clear_memory: Whether to clear archived data from memory
        
        Returns:
        - Whether archiving was successful
        """
        try:
            now = datetime.now()
            archive_dir = os.path.join("Archive")
            os.makedirs(archive_dir, exist_ok=True)
            
            # Calculate time range based on period
            if period == "daily":
                yesterday = (now - timedelta(days=1)).date()
                start_time = datetime.combine(yesterday, datetime.min.time())
                end_time = start_time + timedelta(days=1)
                archive_file = os.path.join(archive_dir, f"daily_{yesterday.isoformat()}.csv")
            elif period == "monthly":
                first_day_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                end_time = first_day_this_month
                start_time = (end_time - timedelta(days=1)).replace(day=1)
                archive_file = os.path.join(archive_dir, f"monthly_{start_time.year:04d}-{start_time.month:02d}.csv")
            else:
                raise ValueError(f"Invalid period: {period}")
            
            # Archive readings for each meter
            all_readings = []
            for meter_id, account in self.accounts.items():
                # Get readings for the period
                period_readings = {
                    ts: reading 
                    for ts, reading in account.meter_readings.items() 
                    if start_time <= ts < end_time
                }
                
                if period_readings:
                    # Add to collection
                    for ts, reading in period_readings.items():
                        all_readings.append({
                            "meter_id": meter_id,
                            "timestamp": ts.isoformat(),
                            "reading": reading
                        })
                    
                    # Clear from memory if requested
                    if clear_memory:
                        for ts in period_readings.keys():
                            del account.meter_readings[ts]
            
            # Save to CSV if we have readings
            if all_readings:
                with open(archive_file, "w", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=["meter_id", "timestamp", "reading"])
                    writer.writeheader()
                    writer.writerows(all_readings)
            
            logger.info(f"Successfully archived {period} readings")
            return True
            
        except Exception as e:
            logger.error(f"Error during {period} archiving: {str(e)}")
            return False

# Create FastAPI application
app = FastAPI(title="Power Consumption Management API System")
ems = APIs()

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
    Receive Meter Reading
    
    Parameters:
    - meter_id: Meter ID
    - timestamp: Timestamp (format: YYYY-MM-DDTHH:mm:00, must be on the hour or half hour)
    - reading: Reading value
    
    Example:
    ```
    /receive_meter_reading?meter_id=123-456-789&timestamp=2025-02-08T01:00:00&reading=100.5
    ```
    """
    try:
        success = ems.record_meter_reading(meter_id, timestamp, reading)
        return MeterReadingResponse(
            success=success,
            message="Reading recorded successfully"
        )
    except ValueError as e:
        error_msg = str(e)
        logger.error(f"Failed to record meter reading: {error_msg}")
        raise HTTPException(
            status_code=400,
            detail=error_msg
        )

@app.get("/get_consumption", response_model=ConsumptionResponse)
async def get_consumption(meter_id: str, period: str):
    """
    Query power consumption for specified period
    
    Parameters:
    - meter_id: Meter ID
    - period: Query period ('last_30min', 'today', 'this_week', 'this_month', 'last_month')
    
    Example:
    ```
    /get_consumption?meter_id=123-456-789&period=this_month
    ```
    """
    try:
        consumption = ems.get_consumption(meter_id, period)
        if consumption is None:
            raise HTTPException(status_code=404, detail="Meter not found or invalid period")
        return ConsumptionResponse(
            meter_id=meter_id,
            period=period,
            **consumption
        )
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/get_last_month_bill", response_model=BillingDetailsResponse)
async def get_last_month_bill(meter_id: str):
    """
    Get last month's bill details
    
    Parameters:
    - meter_id: Meter ID
    
    Returns:
    - period: Billing period (YYYY-MM)
    - start_reading: Initial reading (kWh)
    - end_reading: Final reading (kWh)
    - consumption: Total power consumption (kWh)
    - start_time: First reading timestamp
    - end_time: Last reading timestamp
    
    Example:
    ```
    /get_last_month_bill?meter_id=123-456-789
    ```
    """
    try:
        bill_details = ems.get_last_month_bill(meter_id)
        if bill_details is None:
            raise HTTPException(status_code=404, detail="Meter not found")
        return {
            "meter_id": meter_id,
            **bill_details
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/archive_and_prepare", response_model=ArchiveResponse)
async def archive_and_prepare(period: str):
    """
    Archive readings for specified period
    
    Parameters:
    - period: Archive period ('daily' or 'monthly')
    
    Example:
    ```
    /archive_and_prepare?period=daily
    ```
    """
    if period not in ['daily', 'monthly']:
        raise HTTPException(status_code=400, detail="Invalid period. Must be 'daily' or 'monthly'")
    
    success = ems.archive_readings(period)
    return ArchiveResponse(
        success=success,
        message=f"Successfully archived {period} readings" if success else "Failed to archive readings",
        period=period
    )
