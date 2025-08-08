from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from ..db import get_db
from ..models import Driver, DriverScore, Event, Trip
from ..persistence import get_driver_events, get_driver_trips, get_driver_scores, get_event_stats
from sqlalchemy import func
from datetime import date

router = APIRouter()

@router.get("/drivers")
def list_drivers(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """Get list of all drivers with their current scores."""
    try:
        # Get only the first 3 drivers (tracks 1, 2, 3)
        drivers = db.query(Driver).filter(Driver.external_id.in_([
            "driver_1", "driver_2", "driver_3"
        ])).all()
        
        # If drivers don't exist, create them
        if len(drivers) < 3:
            existing_ids = [d.external_id for d in drivers]
            for i in range(1, 4):
                driver_id = f"driver_{i}"
                if driver_id not in existing_ids:
                    driver = Driver(
                        external_id=driver_id,
                        name=f"Driver {i}"
                    )
                    db.add(driver)
            db.commit()
            drivers = db.query(Driver).filter(Driver.external_id.in_([
                "driver_1", "driver_2", "driver_3"
            ])).all()
        
        # Get latest scores for each driver
        latest_scores = db.query(
            DriverScore.driver_id,
            func.max(DriverScore.created_at).label('latest_score_date')
        ).group_by(DriverScore.driver_id).subquery()
        
        scores = db.query(DriverScore).join(
            latest_scores,
            (DriverScore.driver_id == latest_scores.c.driver_id) &
            (DriverScore.created_at == latest_scores.c.latest_score_date)
        ).all()
        
        # Create a map of driver_id to score
        score_map = {score.driver_id: score for score in scores}
        
        # Build response
        result = []
        for driver in drivers:
            driver_data = {
                "id": driver.id,
                "external_id": driver.external_id,
                "name": driver.name,
                "created_at": driver.created_at.isoformat() if driver.created_at else None,
                "current_score": None
            }
            
            # Add score if available
            if driver.id in score_map:
                score = score_map[driver.id]
                driver_data["current_score"] = {
                    "risk_score": score.risk_score,
                    "avg_speed": score.avg_speed,
                    "overspeed_count": score.overspeed_count,
                    "harsh_brake_count": score.harsh_brake_count,
                    "idle_count": score.idle_count,
                    "date": score.date.isoformat() if score.date else None
                }
            
            result.append(driver_data)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/events")
def list_events(
    db: Session = Depends(get_db),
    driver_id: Optional[int] = Query(None, description="Filter by driver ID"),
    limit: int = Query(100, ge=1, le=1000, description="Number of events to return"),
    offset: int = Query(0, ge=0, description="Number of events to skip")
) -> List[Dict[str, Any]]:
    """Get list of events with optional filtering."""
    try:
        query = db.query(Event)
        
        if driver_id:
            query = query.filter(Event.driver_id == driver_id)
        
        events = query.order_by(Event.timestamp.desc()).offset(offset).limit(limit).all()
        
        result = []
        for event in events:
            event_data = {
                "id": event.id,
                "driver_id": event.driver_id,
                "trip_id": event.trip_id,
                "event_type": event.event_type,
                "timestamp": event.timestamp.isoformat() if event.timestamp else None,
                "lat": event.lat,
                "lon": event.lon,
                "speed_kph": event.speed_kph,
                "acceleration_kph_s": event.acceleration_kph_s,
                "meta": event.meta,
                "created_at": event.created_at.isoformat() if event.created_at else None
            }
            result.append(event_data)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/events/stats")
def get_events_stats(
    db: Session = Depends(get_db),
    driver_id: Optional[int] = Query(None, description="Filter by driver ID")
) -> Dict[str, Any]:
    """Get event statistics."""
    try:
        stats = get_event_stats(db, driver_id)
        return stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/drivers/{driver_id}/events")
def get_driver_events_endpoint(
    driver_id: int,
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=1000, description="Number of events to return"),
    offset: int = Query(0, ge=0, description="Number of events to skip")
) -> List[Dict[str, Any]]:
    """Get events for a specific driver."""
    try:
        events = get_driver_events(db, driver_id, limit, offset)
        
        result = []
        for event in events:
            event_data = {
                "id": event.id,
                "driver_id": event.driver_id,
                "trip_id": event.trip_id,
                "event_type": event.event_type,
                "timestamp": event.timestamp.isoformat() if event.timestamp else None,
                "lat": event.lat,
                "lon": event.lon,
                "speed_kph": event.speed_kph,
                "acceleration_kph_s": event.acceleration_kph_s,
                "meta": event.meta,
                "created_at": event.created_at.isoformat() if event.created_at else None
            }
            result.append(event_data)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/drivers/{driver_id}/trips")
def get_driver_trips_endpoint(
    driver_id: int,
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=500, description="Number of trips to return"),
    offset: int = Query(0, ge=0, description="Number of trips to skip")
) -> List[Dict[str, Any]]:
    """Get trips for a specific driver."""
    try:
        trips = get_driver_trips(db, driver_id, limit, offset)
        
        result = []
        for trip in trips:
            trip_data = {
                "id": trip.id,
                "track_id": trip.track_id,
                "driver_id": trip.driver_id,
                "start_time": trip.start_time.isoformat() if trip.start_time else None,
                "end_time": trip.end_time.isoformat() if trip.end_time else None,
                "created_at": trip.created_at.isoformat() if trip.created_at else None
            }
            result.append(trip_data)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/drivers/{driver_id}/scores")
def get_driver_scores_endpoint(
    driver_id: int,
    db: Session = Depends(get_db),
    days: int = Query(30, ge=1, le=365, description="Number of days to look back")
) -> List[Dict[str, Any]]:
    """Get scores for a specific driver."""
    try:
        scores = get_driver_scores(db, driver_id, days)
        
        result = []
        for score in scores:
            score_data = {
                "id": score.id,
                "driver_id": score.driver_id,
                "date": score.date.isoformat() if score.date else None,
                "avg_speed": score.avg_speed,
                "overspeed_count": score.overspeed_count,
                "harsh_brake_count": score.harsh_brake_count,
                "idle_count": score.idle_count,
                "risk_score": score.risk_score,
                "created_at": score.created_at.isoformat() if score.created_at else None
            }
            result.append(score_data)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# Note: start_simulation and stop_simulation endpoints are now in main.py
# to avoid circular imports with the simulator module
