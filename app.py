import APIs
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, validator
import uvicorn
from datetime import datetime
import asyncio
from typing import Optional
from enum import Enum

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
    if system_state.is_maintenance_mode:

        raise HTTPException(status_code=503, detail="System is in maintenance mode")
    if not system_state.is_receiving_data:
        raise HTTPException(status_code=503, detail="System is not receiving data")
    try:
        meter_id = api_system.register_account(owner_name, address, meter_id)
        return {"meter_id": meter_id, "message": "Account successfully created"}
    except ValueError as e:
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
    if system_state.is_maintenance_mode:
        raise HTTPException(status_code=503, detail="System is in maintenance mode")
    if not system_state.is_receiving_data:
        raise HTTPException(status_code=503, detail="System is not receiving data")
    
    # 验证时间戳是否在整点或半点
    if timestamp.minute not in [0, 30] or timestamp.second != 0:
        raise HTTPException(
            status_code=400, 
            detail="Timestamp must be on the hour (HH:00:00) or half hour (HH:30:00)"
        )
    
    success = api_system.record_meter_reading(meter_id, timestamp, reading)
    return {
        "success": success,
        "message": "Reading recorded successfully" if success else "Failed to record reading"
    }

@app.get("/get_consumption")
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
    if system_state.is_maintenance_mode:
        raise HTTPException(status_code=503, detail="System is in maintenance mode")
    consumption = api_system.get_consumption(meter_id, period)
    if consumption is None:
        raise HTTPException(status_code=404, detail="Meter not found or invalid period")
    return {
        "consumption": consumption,
        "period": period,
        "meter_id": meter_id
    }

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
    return SystemResponse(
        success=True,
        message="System resumed receiving data",
        timestamp=datetime.now().isoformat(),
        is_receiving_data=True
    )

if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)

# After server starts, you can access API documentation at:
# Swagger UI: http://localhost:8000/docs
# ReDoc: http://localhost:8000/redoc