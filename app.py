import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, validator
import uvicorn
from datetime import datetime
import asyncio
from typing import Optional
from enum import Enum
from restore import DataRestorer
from APIs import APIs  # Import the APIs class directly
from loggers import logger

# Create FastAPI application
app = FastAPI(title="Power Consumption Management System")

# Create API instance
api_system = APIs()  # Use the correct class name

# Define maintenance types
class MaintenanceType(str, Enum):
    DAILY = "daily"
    MONTHLY = "monthly"
    BOTH = "both"

# System state control
class SystemState:
    def __init__(self):
        self.is_maintenance_mode = False
        self.is_receiving_data = True

system_state = SystemState()

# Request Models
class MeterReadingRequest(BaseModel):
    meter_id: str
    timestamp: datetime
    reading: float

    @validator('timestamp')
    def validate_timestamp(cls, v):
        # 验证时间戳是否在整点或半点
        if v.minute not in [0, 30] or v.second != 0:
            raise ValueError("Timestamp must be on the hour (HH:00:00) or half hour (HH:30:00)")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "meter_id": "123-456-789",
                "timestamp": "2025-02-08T01:00:00",
                "reading": 100.5
            }
        }

# Response Models
class MaintenanceResponse(BaseModel):
    success: bool
    message: str
    timestamp: str
    maintenance_type: Optional[str] = None

class SystemResponse(BaseModel):
    success: bool
    message: str
    timestamp: str
    is_receiving_data: bool

class BillingResponse(BaseModel):
    success: bool
    message: str
    timestamp: str
    current_month_consumption: Optional[float] = None
    last_month_consumption: Optional[float] = None

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

class RestoreResponse(BaseModel):
    success: bool
    message: str
    timestamp: str
    restored_meters_count: int
    restored_readings_count: int

class ConsumptionResponse(BaseModel):
    meter_id: str
    period: str
    start_reading: float
    end_reading: float
    consumption: float
    start_time: str
    end_time: str

# API endpoints
@app.post("/register_account")
async def register_account(owner_name: str, address: str, meter_id: str):
    """
    Register new account
    
    Parameters:
    - owner_name: Owner name
    - address: Address
    - meter_id: Meter ID
    
    Example:
    ```
    /register_account?owner_name=Adam&address=USA&meter_id=123-456-789
    ```
    """
    logger.info(f"Received registration request for {meter_id}")
    if system_state.is_maintenance_mode:
        logger.warning("Registration failed due to maintenance mode")
        raise HTTPException(status_code=503, detail="System is in maintenance mode")
    try:
        meter_id = api_system.register_account(owner_name, address, meter_id)
        logger.info(f"Account registered successfully: {meter_id}")
        return {"meter_id": meter_id, "message": "Account successfully created"}
    except ValueError as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/receive_meter_reading")
async def receive_meter_reading(meter_id: str, timestamp: datetime, reading: float):
    """
    Receive meter reading
    
    Parameters:
    - meter_id: Meter ID
    - timestamp: Timestamp (format: YYYY-MM-DDTHH:mm:00, must be on the hour or half hour)
    - reading: Reading value
    
    Example:
    ```
    /receive_meter_reading?meter_id=123-456-789&timestamp=2025-02-08T01:00:00&reading=100.5
    ```
    """
    logger.info(f"Received meter reading request for meter ID: {meter_id} at timestamp: {timestamp}")

    try:
        success = api_system.record_meter_reading(meter_id, timestamp, reading)
        logger.info(f"Meter reading successfully recorded for meter ID: {meter_id}")
        return {
            "success": success,
            "message": "Reading recorded successfully" if success else "Failed to record reading"
        }
    except ValueError as e:
        logger.error(f"Failed to record meter reading: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/get_consumption", response_model=ConsumptionResponse)
async def get_consumption(meter_id: str, period: str):
    """
    Query power consumption
    
    Parameters:
    - meter_id: Meter ID
    - period: Query period ('last_30min', 'today', 'this_week', 'this_month', 'last_month')
    
    Returns:
    - meter_id: Meter ID
    - period: Query period
    - start_reading: First reading (kWh)
    - end_reading: Last reading (kWh)
    - consumption: Power consumption (kWh)
    - start_time: First reading timestamp
    - end_time: Last reading timestamp
    
    Errors:
    - 400: Parameter error (invalid period) or insufficient data
    - 404: Meter ID not found or no data in specified period
    
    Example:
    ```
    /get_consumption?meter_id=123-456-789&period=this_month
    ```
    """
    logger.info(f"Received request to get consumption for meter ID: {meter_id}, period: {period}")

    try:
        consumption_data = api_system.get_consumption(meter_id, period)
        logger.info(f"Consumption retrieved successfully for meter ID: {meter_id}, period: {period}")
        return ConsumptionResponse(
            meter_id=meter_id,
            period=period,
            **consumption_data
        )
    except ValueError as e:
        error_msg = str(e)
        logger.error(f"Error getting consumption: {error_msg}")
        if "Meter ID" in error_msg:
            # Meter ID not found
            raise HTTPException(status_code=404, detail=error_msg)
        elif "Invalid period" in error_msg:
            # Invalid period parameter
            raise HTTPException(status_code=400, detail=error_msg)
        elif "No readings found" in error_msg or "Insufficient readings" in error_msg:
            # No data or insufficient data in specified period
            raise HTTPException(status_code=404, detail=error_msg)
        else:
            # Other ValueError errors
            raise HTTPException(status_code=400, detail=error_msg)
    except FileNotFoundError as e:
        # Archive file not found
        logger.error(f"Archive file not found: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        # Other unexpected errors
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Maintenance related functions
async def perform_daily_maintenance():
    """Perform daily maintenance tasks"""
    success = api_system.archive_readings("daily", clear_memory=False)  # Daily maintenance doesn't clear memory
    return MaintenanceResponse(
        success=success,
        message="Daily maintenance completed" if success else "Daily maintenance failed",
        timestamp=datetime.now().isoformat(),
        maintenance_type="daily"
    )

async def perform_monthly_maintenance(meter_id: str):
    """Perform monthly maintenance tasks"""
    archive_success = api_system.archive_readings("monthly", clear_memory=True)  # Monthly maintenance clears memory
    current_month = api_system.get_consumption(meter_id, "this_month")
    last_month = api_system.get_last_month_bill(meter_id)
    
    return BillingResponse(
        success=archive_success,
        message="Monthly maintenance completed" if archive_success else "Monthly maintenance failed",
        timestamp=datetime.now().isoformat(),
        current_month_consumption=current_month,
        last_month_consumption=last_month
    )

@app.post("/maintenance/start", response_model=MaintenanceResponse)
async def start_maintenance(maintenance_type: MaintenanceType):
    """
    Start maintenance task manually
    
    Parameters:
    - maintenance_type: Maintenance type
        - daily: Daily maintenance only
        - monthly: Monthly maintenance only
        - both: Both daily and monthly maintenance
    
    Example:
    ```
    /maintenance/start?maintenance_type=daily
    ```
    """
    if system_state.is_maintenance_mode:
        raise HTTPException(status_code=400, detail="System is already in maintenance mode")
    
    system_state.is_maintenance_mode = True
    try:
        if maintenance_type in [MaintenanceType.DAILY, MaintenanceType.BOTH]:
            daily_result = await perform_daily_maintenance()
            if not daily_result.success:
                raise HTTPException(status_code=500, detail="Daily maintenance failed")
        
        if maintenance_type in [MaintenanceType.MONTHLY, MaintenanceType.BOTH]:
            for meter_id in api_system.accounts.keys():
                monthly_result = await perform_monthly_maintenance(meter_id)
                if not monthly_result.success:
                    raise HTTPException(status_code=500, detail=f"Monthly maintenance failed for meter {meter_id}")
        
        return MaintenanceResponse(
            success=True,
            message=f"{maintenance_type.value} maintenance completed successfully",
            timestamp=datetime.now().isoformat(),
            maintenance_type=maintenance_type.value
        )
    
    except Exception as e:
        system_state.is_maintenance_mode = False
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        system_state.is_maintenance_mode = False

@app.get("/maintenance/status")
async def get_maintenance_status():
    """
    Get current system maintenance status
    
    Returns:
    - is_maintenance_mode: Whether in maintenance mode
    - is_receiving_data: Whether receiving data
    - timestamp: Current timestamp
    
    Example:
    ```
    /maintenance/status
    ```
    """
    return {
        "is_maintenance_mode": system_state.is_maintenance_mode,
        "is_receiving_data": system_state.is_receiving_data,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/shutdown", response_model=SystemResponse)
async def shutdown():
    """
    Stop system data reception
    
    Notes:
    - System will stop receiving new meter readings
    - Does not affect data query functionality
    - Can resume data reception via /resume
    """
    if not system_state.is_receiving_data:
        raise HTTPException(status_code=400, detail="System is already shut down")
    
    system_state.is_receiving_data = False
    api_system.shutdown_system()  # Sync API system status
    
    return SystemResponse(
        success=True,
        message="System stopped receiving data",
        timestamp=datetime.now().isoformat(),
        is_receiving_data=False
    )

@app.post("/resume", response_model=SystemResponse)
async def resume():
    """
    Resume system data reception
    
    Notes:
    - System will resume receiving new meter readings
    - Used for system recovery after shutdown
    """
    if system_state.is_receiving_data:
        raise HTTPException(status_code=400, detail="System is already receiving data")
    
    system_state.is_receiving_data = True
    api_system.resume_system()  # Sync API system status
    
    return SystemResponse(
        success=True,
        message="System resumed receiving data",
        timestamp=datetime.now().isoformat(),
        is_receiving_data=True
    )

@app.get("/get_last_month_bill", response_model=BillingDetailsResponse)
async def get_last_month_bill(meter_id: str):
    """
    Get last month's bill details
    
    Parameters:
    - meter_id: Meter ID
    
    Returns:
    - period: Billing period (YYYY-MM)
    - start_reading: First reading of the month (kWh)
    - end_reading: Last reading of the month (kWh)
    - consumption: Total power consumption (kWh)
    - start_time: First reading timestamp
    - end_time: Last reading timestamp
    
    Example:
    ```
    /get_last_month_bill?meter_id=123-456-789
    ```
    """
    logger.info(f"Received request to get last month's bill for meter ID: {meter_id}")
    
    try:
        bill_details = api_system.get_last_month_bill(meter_id)
        if bill_details is None:
            logger.error(f"Meter ID {meter_id} not found")
            raise HTTPException(status_code=404, detail="Meter not found")
            
        response = {
            "meter_id": meter_id,
            **bill_details
        }
        
        logger.info(f"Bill details retrieved successfully for meter ID: {meter_id}")
        return response
        
    except FileNotFoundError as e:
        logger.error(f"Archive file not found: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        logger.error(f"Error retrieving bill details: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/restore_data", response_model=RestoreResponse)
async def restore_data():
    """
    Restore meter readings data from Archive and logs
    
    Notes:
    1. Restore archived data from Archive directory (from month start to yesterday)
    2. Restore unarchived data from today's log file
    3. Load restored data into system memory
    
    Returns:
    - success: Whether successful
    - message: Processing result message
    - timestamp: Processing time
    - restored_meters_count: Number of meters restored
    - restored_readings_count: Total number of readings restored
    """
    try:
        logger.info("Starting data restoration process")
        restorer = DataRestorer()
        restored_data = restorer.restore_data()
        
        # Update system data
        total_readings = 0
        for meter_id, readings in restored_data.items():
            if meter_id in api_system.accounts:
                api_system.accounts[meter_id].meter_readings.update(readings)
                total_readings += len(readings)
        
        logger.info(f"Successfully restored {len(restored_data)} meters and {total_readings} readings")
        return RestoreResponse(
            success=True,
            message="Data restored successfully",
            timestamp=datetime.now().isoformat(),
            restored_meters_count=len(restored_data),
            restored_readings_count=total_readings
        )
    except Exception as e:
        logger.error(f"Error during data restoration: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Data restoration failed: {str(e)}"
        )

if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)

# After server starts, you can access API documentation at:
# Swagger UI: http://localhost:8000/docs
# ReDoc: http://localhost:8000/redoc