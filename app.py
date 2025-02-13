import APIs
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, validator
import uvicorn
from datetime import datetime
import asyncio
from typing import Optional
from enum import Enum
from restore import DataRestorer

from loggers import logger


# 创建 FastAPI 应用
app = FastAPI(title="Power Consumption Management System")

# 创建API实例
api_system = APIs.ElectricityManagementSystem()

# 定义维护类型
class MaintenanceType(str, Enum):
    DAILY = "daily"
    MONTHLY = "monthly"
    BOTH = "both"

# 系统状态控制
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
    consumption: float

# API endpoints
@app.post("/register_account")
async def register_account(owner_name: str, address: str, meter_id: str):
    """
    注册新账户
    
    参数:
    - owner_name: 用户名
    - address: 地址
    - meter_id: 电表ID
    
    示例:
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
    查询用电量
    
    参数:
    - meter_id: 电表ID
    - period: 查询周期 ('last_30min', 'today', 'this_week', 'this_month', 'last_month')
    
    返回:
    - meter_id: 电表ID
    - period: 查询周期
    - consumption: 用电量
    
    错误:
    - 400: 参数错误（无效的period）或数据不足
    - 404: 电表ID不存在或指定时间段内无数据
    
    示例:
    ```
    /get_consumption?meter_id=123-456-789&period=this_month
    ```
    """
    logger.info(f"Received request to get consumption for meter ID: {meter_id}, period: {period}")

    try:
        consumption = api_system.get_consumption(meter_id, period)
        logger.info(f"Consumption retrieved successfully for meter ID: {meter_id}, period: {period}")
        return ConsumptionResponse(
            meter_id=meter_id,
            period=period,
            consumption=consumption
        )
    except ValueError as e:
        error_msg = str(e)
        logger.error(f"Error getting consumption: {error_msg}")
        if "Meter ID" in error_msg:
            # 电表ID不存在
            raise HTTPException(status_code=404, detail=error_msg)
        elif "Invalid period" in error_msg:
            # 无效的period参数
            raise HTTPException(status_code=400, detail=error_msg)
        elif "No readings found" in error_msg or "Insufficient readings" in error_msg:
            # 指定时间段内无数据或数据不足
            raise HTTPException(status_code=404, detail=error_msg)
        else:
            # 其他ValueError错误
            raise HTTPException(status_code=400, detail=error_msg)
    except FileNotFoundError as e:
        # 找不到归档文件
        logger.error(f"Archive file not found: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        # 其他未预期的错误
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# 维护模式相关函数
async def perform_daily_maintenance():
    """执行每日维护任务"""
    success = api_system.archive_readings("daily", clear_memory=False)  # 日度维护不清除内存
    return MaintenanceResponse(
        success=success,
        message="Daily maintenance completed" if success else "Daily maintenance failed",
        timestamp=datetime.now().isoformat(),
        maintenance_type="daily"
    )

async def perform_monthly_maintenance(meter_id: str):
    """执行月度维护任务"""
    archive_success = api_system.archive_readings("monthly", clear_memory=True)  # 月度维护清除内存
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
    手动启动维护任务
    
    参数:
    - maintenance_type: 维护类型
        - daily: 仅执行日度维护
        - monthly: 仅执行月度维护
        - both: 同时执行日度和月度维护
    
    示例:
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
    获取系统当前维护状态
    
    返回:
    - is_maintenance_mode: 是否处于维护模式
    - is_receiving_data: 是否正在接收数据
    - timestamp: 当前时间戳
    
    示例:
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
    停止系统接收数据
    
    说明:
    - 系统将停止接收新的电表读数
    - 不影响数据查询功能
    - 可以通过/resume恢复数据接收
    """
    if not system_state.is_receiving_data:
        raise HTTPException(status_code=400, detail="System is already shut down")
    
    system_state.is_receiving_data = False
    api_system.shutdown_system()  # 同步API系统状态
    
    return SystemResponse(
        success=True,
        message="System stopped receiving data",
        timestamp=datetime.now().isoformat(),
        is_receiving_data=False
    )

@app.post("/resume", response_model=SystemResponse)
async def resume():
    """
    恢复系统接收数据
    
    说明:
    - 系统将恢复接收新的电表读数
    - 用于shutdown后的系统恢复
    """
    if system_state.is_receiving_data:
        raise HTTPException(status_code=400, detail="System is already receiving data")
    
    system_state.is_receiving_data = True
    api_system.resume_system()  # 同步API系统状态
    
    return SystemResponse(
        success=True,
        message="System resumed receiving data",
        timestamp=datetime.now().isoformat(),
        is_receiving_data=True
    )

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
    从Archive和日志文件恢复本月的meter readings数据
    
    说明:
    1. 从Archive目录恢复本月已归档的数据（从月初到昨天）
    2. 从今天的日志文件恢复未归档的数据
    3. 将恢复的数据加载到系统内存中
    
    返回:
    - success: 是否成功
    - message: 处理结果信息
    - timestamp: 处理时间
    - restored_meters_count: 恢复的电表数量
    - restored_readings_count: 恢复的读数记录总数
    """
    try:
        logger.info("Starting data restoration process")
        restorer = DataRestorer()
        restored_data = restorer.restore_data()
        
        # 更新系统中的数据
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