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
    consumption: float

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
            
        Raises:
            ValueError: If no readings found or insufficient readings in the time period
        """
        logger.info(f"Calculating consumption for meter {self.meter_id} from {start_time} to {end_time}")
        
        # 获取时间范围内的读数
        relevant_readings = {ts: reading for ts, reading in self.meter_readings.items() if start_time <= ts <= end_time}
        
        if not relevant_readings:
            error_msg = f"No readings found for meter {self.meter_id} between {start_time} and {end_time}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        timestamps = sorted(relevant_readings.keys())
        if len(timestamps) < 2:
            error_msg = (f"Insufficient readings for meter {self.meter_id} between {start_time} and {end_time}. "
                        f"Found {len(timestamps)} reading(s), minimum 2 readings required.")
            logger.error(error_msg)
            raise ValueError(error_msg)

        consumption = relevant_readings[timestamps[-1]] - relevant_readings[timestamps[0]]
        logger.info(f"Calculated consumption for meter {self.meter_id}: {consumption} kWh")
        return consumption

class ElectricityManagementSystem:
    """Main Electricity Management System class implementing core API functionality"""
    
    def __init__(self):
        self.accounts: Dict[str, ElectricityAccount] = {}
        self.archived_readings: Dict[str, Dict[str, Dict[datetime, float]]] = {}
        self.is_receiving_data = True
        self._load_accounts()
    
    def _load_accounts(self):
        """从account.csv加载已有账户"""
        try:
            account_file = os.path.join(os.getcwd(), "account.csv")
            if os.path.exists(account_file):
                df = pd.read_csv(account_file, sep='\t')
                for _, row in df.iterrows():
                    self.accounts[row['meter_id']] = ElectricityAccount(
                        meter_id=row['meter_id'],
                        owner_name=row['owner_name'],
                        address=row['address']
                    )
                logger.info(f"Successfully loaded {len(df)} accounts from account.csv")
        except Exception as e:
            logger.error(f"Error loading accounts from file: {str(e)}")
            raise
    
    def register_account(self, owner_name: str, address: str, meter_id: str) -> str:
        """注册新账户并保存到account.csv"""
        logger.info(f"Attempting to register account: {owner_name}, {address}, {meter_id}")
        
        account_file = os.path.join(os.getcwd(), "account.csv")
        try:
            if os.path.exists(account_file):
                df = pd.read_csv(account_file, sep='\t')
                if meter_id in df['meter_id'].values:
                    error_msg = f"Meter ID {meter_id} already exists in account.csv"
                    logger.warning(error_msg)
                    raise ValueError(error_msg)
            
            # 创建新账户
            self.accounts[meter_id] = ElectricityAccount(meter_id, owner_name, address)
            
            # 保存到account.csv
            new_account = pd.DataFrame([{
                'owner_name': owner_name,
                'address': address,
                'meter_id': meter_id
            }])
            
            if os.path.exists(account_file):
                new_account.to_csv(account_file, sep='\t', mode='a', header=False, index=False)
            else:
                new_account.to_csv(account_file, sep='\t', index=False)
            
            logger.info(f"Successfully registered account with meter ID: {meter_id}")
            return meter_id
            
        except pd.errors.EmptyDataError:
            new_account = pd.DataFrame([{
                'owner_name': owner_name,
                'address': address,
                'meter_id': meter_id
            }])
            new_account.to_csv(account_file, sep='\t', index=False)
            return meter_id
            
        except Exception as e:
            logger.error(f"Error during account registration: {str(e)}")
            raise
    
    def record_meter_reading(self, meter_id: str, timestamp: datetime, reading: float) -> bool:
        """
        Record half-hourly meter reading
        
        Args:
            meter_id: Meter ID
            timestamp: Timestamp (must be on the hour, half-hour, or 23:59)
            reading: Meter reading (kWh)
            
        Returns:
            bool: Whether the data was successfully recorded
            
        Raises:
            ValueError: If system is shutdown or other validation errors
        """
        logger.info(f"Recording meter reading: meter_id={meter_id}, timestamp={timestamp}, reading={reading}")

        # 首先检查系统状态
        if not self.is_receiving_data:
            error_msg = "System is currently shutdown and not accepting new readings"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # 然后检查meter_id是否存在
        if meter_id not in self.accounts:
            error_msg = f"Meter ID {meter_id} not found. Unable to record reading."
            logger.error(error_msg)
            raise ValueError(error_msg)

        # 最后检查时间戳格式
        if not ((timestamp.minute == 0 or timestamp.minute == 30) and timestamp.second == 0):
            error_msg = f"Invalid timestamp format for meter reading: {timestamp}. Must be on the hour (HH:00:00) or half hour (HH:30:00)"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # 所有检查通过后，记录读数
        account = self.accounts[meter_id]
        account.meter_readings[timestamp] = reading
        logger.info(f"Meter reading successfully recorded for meter ID: {meter_id}")
        return True
        
    def shutdown_system(self):
        """关闭系统数据接收"""
        self.is_receiving_data = False
        
    def resume_system(self):
        """恢复系统数据接收"""
        self.is_receiving_data = True

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
        
        if period == 'last_month':
            # 获取上个月的年月
            first_day_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            last_month = first_day_this_month - timedelta(days=1)
            monthly_file = f"monthly_{last_month.strftime('%Y-%m')}.csv"
            archive_path = os.path.join(os.getcwd(), "Archive", monthly_file)
            
            try:
                if not os.path.exists(archive_path):
                    logger.error(f"Monthly archive file not found: {archive_path}")
                    raise FileNotFoundError(f"Archive file for {last_month.strftime('%Y-%m')} not found")
                
                df = pd.read_csv(archive_path)
                # 过滤指定meter_id的数据
                meter_data = df[df['meter_id'] == meter_id]
                if meter_data.empty:
                    logger.error(f"No data found for meter_id {meter_id} in archive file")
                    raise ValueError(f"No data found for meter_id {meter_id} in {last_month.strftime('%Y-%m')}")
                
                # 将时间戳转换为datetime对象
                meter_data['timestamp'] = pd.to_datetime(meter_data['timestamp'])
                # 获取最大和最小读数的差值作为消耗量
                consumption = meter_data['reading'].max() - meter_data['reading'].min()
                return consumption
                
            except pd.errors.EmptyDataError:
                logger.error(f"Archive file is empty: {archive_path}")
                raise ValueError(f"Archive file for {last_month.strftime('%Y-%m')} is empty")
            except pd.errors.ParserError as e:
                logger.error(f"Error parsing archive file: {str(e)}")
                raise ValueError(f"Error parsing archive file for {last_month.strftime('%Y-%m')}: {str(e)}")
            except Exception as e:
                logger.error(f"Unexpected error reading monthly archive file: {str(e)}")
                raise
        
        elif period == 'last_30min':
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
        else:
            return None
            
        return account.calculate_consumption(start_time, end_time)
    
    def get_last_month_bill(self, meter_id: str) -> Optional[Dict]:
        """
        Get last month's bill details
        
        Args:
            meter_id: Meter ID
            
        Returns:
            Dict: Last month's bill details including:
                - start_reading: Month's first reading
                - end_reading: Month's last reading
                - consumption: Total consumption in kWh
                - period: Billing period (YYYY-MM)
                
        Raises:
            FileNotFoundError: If archive file not found
            ValueError: If no data found for meter_id or other validation errors
        """
        now = datetime.now()
        first_day_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_month = first_day_this_month - timedelta(days=1)
        monthly_file = f"monthly_{last_month.strftime('%Y-%m')}.csv"
        archive_path = os.path.join(os.getcwd(), "Archive", monthly_file)
        
        try:
            if not os.path.exists(archive_path):
                logger.error(f"Monthly archive file not found: {archive_path}")
                raise FileNotFoundError(f"Archive file for {last_month.strftime('%Y-%m')} not found")
            
            df = pd.read_csv(archive_path)
            meter_data = df[df['meter_id'] == meter_id]
            
            if meter_data.empty:
                logger.error(f"No data found for meter_id {meter_id} in archive file")
                raise ValueError(f"No data found for meter_id {meter_id} in {last_month.strftime('%Y-%m')}")
            
            # 将时间戳转换为datetime对象并排序
            meter_data['timestamp'] = pd.to_datetime(meter_data['timestamp'])
            meter_data = meter_data.sort_values('timestamp')
            
            # 获取月初和月末读数
            start_reading = meter_data.iloc[0]['reading']
            end_reading = meter_data.iloc[-1]['reading']
            consumption = end_reading - start_reading
            
            return {
                "period": last_month.strftime('%Y-%m'),
                "start_reading": start_reading,
                "end_reading": end_reading,
                "consumption": consumption,
                "start_time": meter_data.iloc[0]['timestamp'].isoformat(),
                "end_time": meter_data.iloc[-1]['timestamp'].isoformat()
            }
            
        except pd.errors.EmptyDataError:
            logger.error(f"Archive file is empty: {archive_path}")
            raise ValueError(f"Archive file for {last_month.strftime('%Y-%m')} is empty")
        except pd.errors.ParserError as e:
            logger.error(f"Error parsing archive file: {str(e)}")
            raise ValueError(f"Error parsing archive file for {last_month.strftime('%Y-%m')}: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error reading monthly archive file: {str(e)}")
            raise

    def archive_readings(self, period: str, clear_memory: bool = False) -> bool:
        """
        Archive meter readings for specified period and prepare for new data
        
        Args:
            period: Archive period ('daily' or 'monthly')
            clear_memory: Whether to clear the archived data from memory after saving
            
        Returns:
            bool: Whether archiving was successful
        """
        logger.info(f"Archiving readings for period: {period}")
        try:
            now = datetime.now()
            archive_dir = os.path.join(os.getcwd(), "Archive")
            os.makedirs(archive_dir, exist_ok=True)

            all_readings = []
            for meter_id, account in self.accounts.items():
                # 根据period类型设置不同的时间范围和文件名
                if period == 'monthly':
                    # 月度归档：获取上个月的年月
                    first_day_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                    last_month = first_day_this_month - timedelta(days=1)
                    archive_key = last_month.strftime('%Y-%m')
                    # 获取上个月的时间范围
                    month_start = last_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                    month_end = first_day_this_month
                else:
                    # 日度归档：获取前一天的日期
                    yesterday = (now - timedelta(days=1)).date()
                    archive_key = yesterday.isoformat()
                    # 获取前一天的时间范围
                    day_start = datetime.combine(yesterday, datetime.min.time())
                    day_end = datetime.combine(yesterday + timedelta(days=1), datetime.min.time())

                filename = f"{period}_{archive_key}.csv"
                
                # 获取需要归档的读数
                if period == 'monthly':
                    period_readings = {ts: reading for ts, reading in account.meter_readings.items() 
                                    if month_start <= ts < month_end}
                else:
                    period_readings = {ts: reading for ts, reading in account.meter_readings.items() 
                                    if day_start <= ts < day_end}

                if period_readings:
                    for timestamp, reading in period_readings.items():
                        all_readings.append({
                            'meter_id': meter_id,
                            'timestamp': timestamp,
                            'reading': reading
                        })

                    if clear_memory:
                        logger.info(f"Clearing memory for archived readings of meter ID: {meter_id}")
                        for ts in period_readings.keys():
                            del account.meter_readings[ts]

            if all_readings:
                df = pd.DataFrame(all_readings)
                df['timestamp'] = df['timestamp'].dt.strftime('%Y-%m-%dT%H:%M:%S')
                csv_path = os.path.join(archive_dir, filename)
                df.to_csv(csv_path, index=False)
                logger.info(f"Archived data saved to {csv_path}")

            return True
        except Exception as e:
            logger.exception(f"Error during archiving process: {str(e)}")
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
    查询用电量
    
    参数:
    - meter_id: 电表ID
    - period: 查询周期 ('last_30min', 'today', 'this_week', 'this_month', 'last_month')
    
    示例:
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
            consumption=consumption
        )
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/get_last_month_bill", response_model=BillingDetailsResponse)
async def get_last_month_bill(meter_id: str):
    """
    获取上月账单详情
    
    参数:
    - meter_id: 电表ID
    
    返回:
    - period: 账单周期 (YYYY-MM)
    - start_reading: 月初读数 (kWh)
    - end_reading: 月末读数 (kWh)
    - consumption: 总用电量 (kWh)
    - start_time: 第一次读数时间
    - end_time: 最后一次读数时间
    
    示例:
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
    归档指定周期的读数数据
    
    参数:
    - period: 归档周期 ('daily' or 'monthly')
    
    示例:
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
