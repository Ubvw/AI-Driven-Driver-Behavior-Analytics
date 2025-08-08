# AI Driver Behavior Analytics MVP

A real-time driver behavior monitoring system built with FastAPI, PostgreSQL, and Chart.js.

## Project Overview

This MVP demonstrates real-time streaming of GPS telemetry data, performs rule-based event detection (overspeeding, harsh braking, sudden acceleration, idling), computes driver risk scores, and visualizes the data on a live dashboard.

## Features

- **Real-time GPS streaming** from CSV simulator with speed calculation
- **Event Detection:** overspeeding, harsh braking, sudden acceleration, idling
- **Driver scoring** with risk assessment (0-100 scale)
- **Live dashboard** with Chart.js visualizations
- **WebSocket communication** for real-time updates
- **PostgreSQL persistence** for events, trips, and scores
- **Driver selection** with data isolation between drivers
- **State persistence** across page refreshes

## Technology Stack

- **Backend:** FastAPI (Python)
- **Database:** PostgreSQL
- **Frontend:** Chart.js, HTML5, JavaScript, Tailwind CSS
- **Real-time:** WebSocket
- **Data:** GeoLife GPS trajectory dataset
- **Package Manager:** UV

## Quick Start

### Prerequisites

- Python 3.8+
- PostgreSQL
- UV package manager

### Installation

1. **Clone and setup environment:**
   ```bash
   # Install dependencies with UV
   uv sync
   
   # Or if you prefer to install manually:
   uv pip install -r requirements.txt
   ```

2. **Database Setup:**
   ```bash
   # Ensure PostgreSQL is running and create database
   # (Assuming PostgreSQL is already set up as mentioned)
   
   # Initialize database tables
   python -c "from app.db import init_db; init_db()"
   ```

3. **Run the application:**
   ```bash
   uv run uvicorn app.main:app --reload --port 8000
   ```

4. **Access the dashboard:**
   - Open browser: http://127.0.0.1:8000/dashboard
   - API documentation: http://127.0.0.1:8000/docs

## Project Structure

```
ai_driver_behavior_mvp/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entrypoint
│   ├── config.py            # Environment configuration
│   ├── models.py            # SQLAlchemy models
│   ├── db.py               # Database initialization
│   ├── detection.py         # Event detection logic
│   ├── persistence.py       # Database persistence layer
│   ├── simulator.py         # CSV data simulator
│   ├── wsmanager.py         # WebSocket connection manager
│   ├── api/
│   │   ├── __init__.py
│   │   └── endpoints.py    # REST API endpoints
│   └── templates/
│       └── dashboard.html   # Dashboard template
├── tests/
│   ├── __init__.py
│   └── test_detection.py   # Unit tests for detection logic
├── GPS Trajectory/         # Data files
│   ├── go_track_tracks.csv
│   └── go_track_trackspoints.csv
├── requirements.txt
├── pyproject.toml
├── uv.lock
└── README.md
```

## API Endpoints

### Core Endpoints
- `GET /api/drivers` - List all drivers with scores
- `POST /api/start_simulation` - Start GPS simulation
- `POST /api/stop_simulation` - Stop GPS simulation
- `GET /api/simulation_status` - Check simulation status
- `GET /dashboard` - Dashboard page
- `GET /health` - Health check

### Event Management
- `GET /api/events` - List all events with optional filtering
- `GET /api/events/stats` - Get event statistics
- `GET /api/drivers/{driver_id}/events` - Get events for a specific driver
- `GET /api/drivers/{driver_id}/trips` - Get trips for a specific driver
- `GET /api/drivers/{driver_id}/scores` - Get scores for a specific driver

## Configuration

The application uses a comprehensive configuration system with environment variables and runtime overrides.

### Environment Variables

Create a `.env` file in the project root with the following variables:

```bash
# Database Configuration
DATABASE_URL=postgresql://postgres:password@localhost:5432/driverdb

# Simulation Configuration
EMIT_INTERVAL_SECONDS=3.0
SIMULATION_ENABLED=true

# Detection Thresholds
OVERSPEED_KPH=100
HARSH_BRAKE_KPH_S=-10
SUDDEN_ACCEL_KPH_S=10
IDLE_SECONDS_THRESHOLD=600

# Scoring Configuration
SCORE_OVERSPEED_WEIGHT=2
SCORE_HARSH_BRAKE_WEIGHT=3
SCORE_IDLE_WEIGHT=1
SCORE_BASE=100

# WebSocket Configuration
WS_MAX_CONNECTIONS=100
WS_HEARTBEAT_INTERVAL=30

# API Configuration
API_RATE_LIMIT=1000
API_DEFAULT_LIMIT=100
API_MAX_LIMIT=1000

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=%(asctime)s - %(name)s - %(levelname)s - %(message)s
LOG_FILE=driver_analytics.log

# Development Configuration
DEBUG=false
ENABLE_CORS=true
```

### Runtime Configuration

You can update configuration at runtime using the Config class:

```python
from app.config import config

# Update detection thresholds
config.update_detection_thresholds(overspeed_kph=90)

# Update scoring weights
config.update_scoring_weights(overspeed_weight=3)

# Get current configuration
detection_config = config.get_detection_config()
scoring_config = config.get_scoring_config()
```

## Detection Rules

- **Overspeeding:** Speed > 100 km/h
- **Harsh Braking:** Acceleration < -10 km/h/s
- **Sudden Acceleration:** Acceleration > 10 km/h/s
- **Idling:** Speed = 0 for > 600 seconds (10 minutes)

## Scoring Formula

```
Risk Score = max(0, 100 - (overspeed_count*2 + harsh_brake_count*3 + idle_count*1))
```

## Key Features

### Real-time Speed Calculation
The system calculates speed from GPS coordinates using the Haversine formula:
- Distance between consecutive GPS points
- Time difference between points
- Speed = Distance / Time (km/h)

### Driver Data Isolation
- Each driver's data is isolated
- Switching drivers resets all charts and counters
- State persistence across page refreshes

### Event Detection
- Real-time detection of unsafe driving behaviors
- Visual indicators when events are detected
- Event counts displayed in dashboard

### Risk Scoring
- Starts at 100 (perfect score)
- Decreases based on detected events
- Real-time updates via WebSocket

## Development Milestones

This project follows a milestone-based development approach:

- **Milestone 0:** ✅ Environment & DB setup
- **Milestone 1:** ✅ FastAPI skeleton + basic REST endpoints
- **Milestone 2:** ✅ WebSocket manager + dashboard stub
- **Milestone 3:** ✅ Simulator + start/stop control
- **Milestone 4:** ✅ Detection pipeline + unit tests
- **Milestone 5:** ✅ Persistence (events & scores)
- **Milestone 6:** ✅ Dashboard charts & UI polish
- **Milestone 7:** ✅ Integration tests & demo script
- **Milestone 8:** ✅ Hardening & documentation

## Testing

```bash
# Run tests
uv run pytest

# Run specific test file
uv run pytest tests/test_detection.py -v

# Run integration tests
uv run pytest tests/test_integration.py -v

# Run dashboard tests
uv run pytest tests/test_dashboard.py -v

# Manual testing
curl http://127.0.0.1:8000/api/drivers
```

## Data Format

The system uses the GeoLife GPS trajectory dataset:

- **Tracks CSV:** Trip metadata (id, id_android, speed, time, distance, rating)
- **Trackpoints CSV:** GPS points (id, latitude, longitude, track_id, time)

