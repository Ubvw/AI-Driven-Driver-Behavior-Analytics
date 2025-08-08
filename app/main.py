from fastapi import FastAPI, WebSocket, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi import Request
from pydantic import BaseModel
from .db import init_db
from .api.endpoints import router as api_router
from .wsmanager import ConnectionManager
from .simulator import start_simulation, stop_simulation, is_running
import os

class SimulationRequest(BaseModel):
    driver_id: str = None

# Create FastAPI app
app = FastAPI(
    title="AI Driver Behavior Analytics MVP",
    description="Real-time driver behavior monitoring system",
    version="1.0.0"
)

# Setup templates
templates = Jinja2Templates(directory="app/templates")

# Create connection manager
manager = ConnectionManager()

# Include API routes
app.include_router(api_router, prefix="/api")

@app.on_event("startup")
async def startup():
    """Initialize database on startup."""
    init_db()

@app.get("/")
async def root():
    """Root endpoint - redirect to dashboard."""
    return {"message": "AI Driver Behavior Analytics MVP", "dashboard": "/dashboard"}

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Serve the dashboard page."""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

@app.websocket("/ws/data")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time data streaming."""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive - wait for messages
            data = await websocket.receive_text()
            # Optionally handle incoming messages if needed
    except Exception:
        manager.disconnect(websocket)

@app.post("/api/start_simulation")
async def api_start_simulation(request: SimulationRequest, background_tasks: BackgroundTasks):
    """Start the GPS simulation."""
    if is_running():
        return {"message": "Simulation already running"}
    
    # Start simulation in background with selected driver
    background_tasks.add_task(start_simulation, manager, None, None, request.driver_id)
    return {"message": "simulation started"}

@app.post("/api/stop_simulation")
async def api_stop_simulation():
    """Stop the GPS simulation."""
    result = stop_simulation()
    return result

@app.get("/api/simulation_status")
async def api_simulation_status():
    """Get current simulation status."""
    return {"is_running": is_running()}
