# Power Consumption Management API System

## Project Overview
This system is a power consumption management API system developed for the Energy Market Authority (EMA) of Singapore. It provides comprehensive user account management, meter data collection, and query functionality, built using the FastAPI framework for RESTful API services.

## Key Features
1. Account Management
   - New user registration (including meter ID binding)
   - Account information management (including family member information)
   - Meter-to-account mapping maintenance

2. Meter Data Collection
   - Receiving meter readings from IoT devices at 30-minute intervals (on the hour and half-hour)
   - Real-time data storage and multiple validations
   - Automatic validation of reading reasonability and time accuracy
   - Support for batch data import and export (CSV format)

3. Power Consumption Query Functions
   - Last 30-minute consumption (calculated based on reading differences)
   - Daily consumption statistics
   - Weekly consumption statistics
   - Monthly consumption statistics
   - Previous month consumption statistics
   - Support for custom time period queries

4. Bill Query
   - Previous month bill details (in kilowatt-hours)
   - Historical bill queries
   - Bill data archiving functionality

5. Data Management
   - Support for data archiving and preparation
   - Historical data export functionality
   - Data backup and recovery

## Technical Architecture
- Programming Language: Python 3.8+
- Web Framework: FastAPI
- API Documentation: Auto-generated Swagger/OpenAPI documentation
- Data Storage: In-memory data structures (time-series based meter readings)
- Data Format: JSON/CSV
- API Style: RESTful
- ASGI Server: uvicorn

## Data Structures
- Meter Readings: Dictionary with timestamp indexing (records every 30 minutes, 23:59 data automatically normalized to next day 00:00)
- Power Consumption: Real-time calculation based on meter reading differences
- Account Information: Contains basic information and associated meter reading data
- Meter Mapping: Mapping relationship between meter IDs and accounts
- Response Models: Using Pydantic models for data validation and serialization

## Data Validation
- Time Validation: Ensuring readings are at hour marks, half-hour marks, or 23:59
- Reading Validation: Ensuring readings continuously increase
- Meter Validation: Ensuring meter IDs are unique and registered
- Data Normalization: 23:59 readings automatically converted to next day 00:00
- Input Validation: Using Pydantic models for request data validation

## API Endpoints
1. POST /register_account - Register new account
2. POST /receive_meter_reading - Receive meter reading
3. GET /get_consumption - Query power consumption
4. GET /get_last_month_bill - Query last month's bill
5. POST /archive_and_prepare - Archive data

Detailed API documentation can be accessed through the system's /docs endpoint (Swagger UI).

## Deployment Instructions
1. Install dependencies:
   ```bash
   pip install fastapi uvicorn pydantic
   ```
2. Run server:
   ```bash
   uvicorn APIs:app --reload
   ```

## File Description
- APIs.py: Core API implementation and data processing logic
- Import.py: Data import and processing functionality
- daily.py: Daily power consumption statistics functionality
- monthly.py: Monthly power consumption statistics functionality
- main.py: Application entry point
- mapping.csv: Meter and account mapping data
- meter_readings.csv: Meter reading data 