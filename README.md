# Power Consumption Management System

## Overview
A comprehensive power consumption management system that provides RESTful APIs for managing electricity meter readings, account registration, consumption queries, and system maintenance. The system is designed to handle half-hourly meter readings with efficient data archiving and recovery capabilities.

## Key Features

### 1. Account Management
- Register new accounts with owner name, address, and meter ID
- Validate meter ID uniqueness
- Store account information in CSV format
- Support for multiple accounts management

### 2. Meter Reading Collection
- Record half-hourly meter readings (HH:00:00 or HH:30:00)
- Validate timestamp format and reading values
- Real-time data validation
- Automatic data archiving

### 3. Power Consumption Querying
- Multiple query periods supported:
  - Last 30 minutes
  - Today
  - This week
  - This month
  - Last month
- Detailed consumption information:
  - Start reading and timestamp
  - End reading and timestamp
  - Total consumption
  - Period summary

### 4. Monthly Billing
- Automated monthly bill generation
- Structured bill details:
  - Billing period (YYYY-MM)
  - Start and end readings
  - Total consumption
  - Reading timestamps
- Historical bill data archiving

### 5. System Maintenance
- Automated daily maintenance:
  - Archive yesterday's readings to daily_YYYY-MM-DD.csv
  - Clear archived data from memory
  - Maintain data integrity
- Monthly maintenance:
  - Archive last month's readings to monthly_YYYY-MM.csv
  - Generate monthly bills
  - Clear old data from memory
- System control:
  - Maintenance mode support
  - Data reception control
  - System shutdown/resume capability

### 6. Data Recovery
- Comprehensive data recovery functionality:
  - Restore current month's data from daily CSV files in Archive
  - Recover current day's readings from logs
  - Automatic recovery on system startup
  - Support for system recovery after failures

## API Documentation

### Account Management
```
POST /register_account
- Parameters:
  - owner_name: Owner name (string)
  - address: Address (string)
  - meter_id: Meter ID (string)
- Returns:
  - meter_id: Registered meter ID
  - message: Success message
```

### Meter Reading
```
POST /receive_meter_reading
- Parameters:
  - meter_id: Meter ID (string)
  - timestamp: Reading timestamp (YYYY-MM-DDTHH:mm:00)
  - reading: Reading value (float)
- Returns:
  - success: Whether recording was successful
  - message: Processing result message
```

### Power Consumption
```
GET /get_consumption
- Parameters:
  - meter_id: Meter ID (string)
  - period: Query period ('last_30min', 'today', 'this_week', 'this_month', 'last_month')
- Returns:
  - meter_id: Meter ID
  - period: Query period
  - start_reading: First reading (kWh)
  - end_reading: Last reading (kWh)
  - consumption: Total consumption (kWh)
  - start_time: First reading timestamp
  - end_time: Last reading timestamp
```

### Monthly Bill
```
GET /get_last_month_bill
- Parameters:
  - meter_id: Meter ID (string)
- Returns:
  - period: Billing period (YYYY-MM)
  - start_reading: First reading (kWh)
  - end_reading: Last reading (kWh)
  - consumption: Total consumption (kWh)
  - start_time: First reading timestamp
  - end_time: Last reading timestamp
```

### System Maintenance
```
POST /maintenance/start
- Parameters:
  - maintenance_type: Maintenance type ('daily', 'monthly', 'both')
- Returns:
  - success: Whether successful
  - message: Processing result message
  - timestamp: Processing time
  - maintenance_type: Executed maintenance type

GET /maintenance/status
- Returns:
  - is_maintenance_mode: Whether in maintenance mode
  - is_receiving_data: Whether receiving data
  - timestamp: Current timestamp

POST /shutdown
- Returns:
  - success: Whether successful
  - message: Processing result message
  - timestamp: Processing time
  - is_receiving_data: System status

POST /resume
- Returns:
  - success: Whether successful
  - message: Processing result message
  - timestamp: Processing time
  - is_receiving_data: System status
```

### Data Recovery
```
POST /restore_data
- Returns:
  - success: Whether successful
  - message: Processing result message
  - timestamp: Processing time
  - restored_meters_count: Number of meters restored
  - restored_readings_count: Total number of readings restored
```

## Project Structure
```
.
├── APIs.py              # Core API implementation and business logic
├── app.py              # FastAPI application and endpoint definitions
├── restore.py          # Data recovery implementation
├── daily.py            # Daily maintenance service
├── monthly.py          # Monthly maintenance service
├── loggers.py          # Logging configuration
├── account.csv         # Account information storage
├── Archive/            # Archived data storage
│   ├── daily_YYYY-MM-DD.csv    # Daily archived readings
│   └── monthly_YYYY-MM.csv     # Monthly archived readings
└── logs/              # System logs
    └── YYYY-MM-DD.log # Daily log files
```

## Technical Requirements
- Python 3.8+
- FastAPI framework
- Uvicorn ASGI server
- Pandas for data processing
- Pydantic for data validation
- Testing tools (pytest, httpx)
- Development tools (black, flake8, isort)

## Installation
1. Clone the repository
2. Create and activate a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the System
1. Start the main API server:
   ```bash
   uvicorn app:app --host 0.0.0.0 --port 8000
   ```
2. Access the API documentation:
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

## Data Validation Rules
1. Timestamp requirements:
   - Must be on the hour (HH:00:00)
   - Or on the half hour (HH:30:00)
2. Meter readings:
   - Must be numeric values
   - Must be continuously increasing
3. Meter IDs:
   - Must be pre-registered
   - Must be unique in the system

## Error Handling
- 400: Bad Request (Invalid input parameters)
- 404: Not Found (Resource not found)
- 500: Internal Server Error
- 503: Service Unavailable (System in maintenance)

## Logging
- Comprehensive logging system
- Daily log rotation
- Separate logs for:
  - API operations
  - Maintenance tasks
  - System events
  - Error tracking

## Security Considerations
1. Input validation for all API endpoints
2. Error message sanitization
3. Rate limiting support
4. Maintenance mode protection
5. Data integrity checks

## Data Recovery Process
1. Automatic recovery on system startup
2. Recovery sources:
   - Daily CSV files from Archive (current month's data)
   - Current day's log file
3. Recovery validation:
   - Timestamp validation
   - Reading value validation
   - Data consistency checks

## Testing
1. Unit tests with pytest
2. API integration tests with httpx
3. Data validation tests
4. Recovery process tests
5. Error handling tests

## Development Guidelines
1. Code formatting with black
2. Import sorting with isort
3. Code linting with flake8
4. Type hints usage
5. Comprehensive documentation 