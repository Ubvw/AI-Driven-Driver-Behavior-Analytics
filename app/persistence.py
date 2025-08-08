from datetime import datetime, date
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from .models import Driver, Trip, Event, DriverScore
from .db import SessionLocal

def persist_event(
    db: Session,
    trip_id: int,
    driver_id: int,
    timestamp: datetime,
    lat: float,
    lon: float,
    speed_kph: float,
    acceleration_kph_s: float,
    event_type: str,
    meta: Dict = None
) -> Event:
    """Persist an event to the database."""
    event = Event(
        trip_id=trip_id,
        driver_id=driver_id,
        event_type=event_type,
        timestamp=timestamp,
        lat=lat,
        lon=lon,
        speed_kph=speed_kph,
        acceleration_kph_s=acceleration_kph_s,
        meta=meta or {}
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event

def ensure_trip_exists(db: Session, track_id: str, driver_id: int, start_time: datetime) -> Trip:
    """Ensure a trip exists in the database, create if not."""
    trip = db.query(Trip).filter(Trip.track_id == track_id).first()
    
    if not trip:
        trip = Trip(
            track_id=track_id,
            driver_id=driver_id,
            start_time=start_time,
            end_time=None  # Will be updated when trip ends
        )
        db.add(trip)
        db.commit()
        db.refresh(trip)
    
    return trip

def update_trip_end_time(db: Session, track_id: str, end_time: datetime):
    """Update trip end time when trip is completed."""
    trip = db.query(Trip).filter(Trip.track_id == track_id).first()
    if trip:
        trip.end_time = end_time
        db.commit()

def upsert_driver_score(
    db: Session,
    driver_id: int,
    date: date,
    avg_speed: float,
    overspeed_count: int,
    harsh_brake_count: int,
    idle_count: int,
    risk_score: int
) -> DriverScore:
    """Upsert driver score for a specific date."""
    # Check if score exists for this driver and date
    existing_score = db.query(DriverScore).filter(
        DriverScore.driver_id == driver_id,
        DriverScore.date == date
    ).first()
    
    if existing_score:
        # Update existing score
        existing_score.avg_speed = avg_speed
        existing_score.overspeed_count = overspeed_count
        existing_score.harsh_brake_count = harsh_brake_count
        existing_score.idle_count = idle_count
        existing_score.risk_score = risk_score
        db.commit()
        db.refresh(existing_score)
        return existing_score
    else:
        # Create new score
        score = DriverScore(
            driver_id=driver_id,
            date=date,
            avg_speed=avg_speed,
            overspeed_count=overspeed_count,
            harsh_brake_count=harsh_brake_count,
            idle_count=idle_count,
            risk_score=risk_score
        )
        db.add(score)
        db.commit()
        db.refresh(score)
        return score

def get_driver_events(
    db: Session,
    driver_id: int,
    limit: int = 100,
    offset: int = 0
) -> List[Event]:
    """Get recent events for a driver."""
    return db.query(Event).filter(
        Event.driver_id == driver_id
    ).order_by(
        Event.timestamp.desc()
    ).offset(offset).limit(limit).all()

def get_driver_trips(
    db: Session,
    driver_id: int,
    limit: int = 50,
    offset: int = 0
) -> List[Trip]:
    """Get trips for a driver."""
    return db.query(Trip).filter(
        Trip.driver_id == driver_id
    ).order_by(
        Trip.start_time.desc()
    ).offset(offset).limit(limit).all()

def get_driver_scores(
    db: Session,
    driver_id: int,
    days: int = 30
) -> List[DriverScore]:
    """Get driver scores for the last N days."""
    from datetime import timedelta
    start_date = date.today() - timedelta(days=days)
    
    return db.query(DriverScore).filter(
        DriverScore.driver_id == driver_id,
        DriverScore.date >= start_date
    ).order_by(DriverScore.date.desc()).all()

def get_event_stats(db: Session, driver_id: Optional[int] = None) -> Dict:
    """Get event statistics."""
    query = db.query(Event)
    
    if driver_id:
        query = query.filter(Event.driver_id == driver_id)
    
    # Count events by type
    from sqlalchemy import func
    event_counts = db.query(
        Event.event_type,
        func.count(Event.id).label('count')
    ).group_by(Event.event_type).all()
    
    stats = {
        'total_events': sum(count for _, count in event_counts),
        'by_type': {event_type: count for event_type, count in event_counts}
    }
    
    return stats

def cleanup_old_data(db: Session, days_to_keep: int = 90):
    """Clean up old events and scores (optional maintenance function)."""
    from datetime import timedelta
    cutoff_date = date.today() - timedelta(days=days_to_keep)
    
    # Delete old events
    old_events = db.query(Event).filter(
        Event.timestamp < cutoff_date
    ).delete()
    
    # Delete old scores
    old_scores = db.query(DriverScore).filter(
        DriverScore.date < cutoff_date
    ).delete()
    
    db.commit()
    
    return {
        'deleted_events': old_events,
        'deleted_scores': old_scores
    }
