# Power Consumption Management API System

## Project Overview
This system is a power consumption management API system developed for the Energy Market Authority (EMA) of Singapore. It provides comprehensive meter data collection, user account management, and consumption query functionality, built using the FastAPI framework for RESTful API services.

## System Architecture
- **Main API Server** (`app.py`): Core API endpoints and request handling
- **API Implementation** (`APIs.py`): Business logic and data management
- **Daily Maintenance** (`daily.py`): Daily data archiving service
- **Monthly Maintenance** (`monthly.py`): Monthly billing and data archiving service

## Key Features

### 1. Account Management
- Register new accounts with meter ID binding
- Automatic meter ID validation
- Account information storage and retrieval

### 2. Meter Reading Collection
- Receive readings at 30-minute intervals (HH:00:00 or HH:30:00)
- Automatic timestamp validation and normalization
- Real-time data validation (reading continuity check)
- Support for CSV data export

### 3. Consumption Queries
- Last 30 minutes consumption
- Daily consumption
- Weekly consumption
- Monthly consumption
- Previous month consumption
- Custom period queries

### 4. Data Archiving
- Daily archiving (preserves memory data)
- Monthly archiving (clears memory data)
- Automated CSV file generation
- Structured archive directory organization

### 5. System Maintenance
- Maintenance mode support
- Data reception control
- System shutdown/resume functionality
- Automated error handling

## API Endpoints

### Account Management
```
POST /register_account
Parameters:
- owner_name: string
- address: string
- meter_id: string
```

### Meter Reading
```
POST /receive_meter_reading
Parameters:
- meter_id: string
- timestamp: datetime (YYYY-MM-DDTHH:mm:00)
- reading: float
```

### Consumption Queries
```
GET /get_consumption
Parameters:
- meter_id: string
- period: string (last_30min/today/this_week/this_month/last_month)

GET /get_last_month_bill
Parameters:
- meter_id: string
```

### System Maintenance
```
POST /maintenance/start
Parameters:
- maintenance_type: string (daily/monthly/both)

POST /shutdown
POST /resume

GET /maintenance/status
```

## Data Storage
- In-memory data structures for active readings
- CSV file storage for archived data
- Structured archive directory:
  - Daily: `Archive/daily_YYYY-MM-DD.csv`
  - Monthly: `Archive/monthly_YYYY-MM.csv`

## Installation

1. Clone the repository:
```bash
git clone [repository-url]
cd power-consumption-management
```

2. Create a virtual environment (recommended):
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
uvicorn app:app --host localhost --port 8000 --reload
```

2. Start the daily maintenance service:
```bash
uvicorn daily:maintenance_app --host localhost --port 8001 --reload
```

3. Start the monthly maintenance service:
```bash
uvicorn monthly:maintenance_app --host localhost --port 8002 --reload
```

## API Documentation
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Data Validation Rules
1. Timestamp must be either:
   - On the hour (HH:00:00)
   - On the half hour (HH:30:00)
2. Readings must be continuously increasing
3. Meter IDs must be pre-registered
4. All numeric values maintain decimal precision

## Error Handling
- Input validation errors (400)
- Resource not found errors (404)
- System maintenance errors (503)
- Detailed error messages for debugging

## Development Requirements
- Python 3.8+
- FastAPI
- Uvicorn
- Pydantic
- Pandas
- Requests

## Project Structure
```
power-consumption-management/
├── app.py              # Main API server
├── APIs.py             # Core implementation
├── daily.py            # Daily maintenance
├── monthly.py          # Monthly maintenance
├── requirements.txt    # Dependencies
├── README.md          # Documentation
└── Archive/           # Data archive directory
    ├── daily_*.csv    # Daily archives
    └── monthly_*.csv  # Monthly archives
``` 