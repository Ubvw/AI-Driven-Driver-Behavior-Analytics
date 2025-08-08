from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, List
from .config import (
    OVERSPEED_KPH, 
    HARSH_BRAKE_KPH_S, 
    SUDDEN_ACCEL_KPH_S, 
    IDLE_SECONDS_THRESHOLD
)

# In-memory state for each driver
driver_states: Dict[str, Dict] = {}

def compute_acceleration(prev_speed_kph: float, prev_ts: datetime, speed_kph: float, ts: datetime) -> float:
    """Compute acceleration in km/h per second (kph/s)."""
    delta_s = (ts - prev_ts).total_seconds()
    if delta_s <= 0.0:
        # Avoid division by zero; treat as zero acceleration
        return 0.0
    return (speed_kph - prev_speed_kph) / delta_s

def detect_events(
    driver_id: str,
    timestamp: datetime,
    lat: float,
    lon: float,
    speed_kph: float,
    acceleration_kph_s: float
) -> List[Dict]:
    """Detect driving events based on current telemetry."""
    events = []
    
    # Initialize driver state if not exists
    if driver_id not in driver_states:
        driver_states[driver_id] = {
            'last_speed_kph': speed_kph,
            'last_timestamp': timestamp,
            'current_idle_start_ts': None,
            'overspeed_count': 0,
            'harsh_brake_count': 0,
            'sudden_accel_count': 0,
            'idle_count': 0,
            'last_non_zero_speed_ts': timestamp if speed_kph > 0 else None
        }
    
    state = driver_states[driver_id]
    
    # Check for overspeeding
    if speed_kph > OVERSPEED_KPH:
        events.append({
            'event_type': 'overspeeding',
            'timestamp': timestamp.isoformat(),
            'lat': lat,
            'lon': lon,
            'speed_kph': speed_kph,
            'acceleration_kph_s': acceleration_kph_s,
            'meta': {'threshold': OVERSPEED_KPH}
        })
        state['overspeed_count'] += 1
    
    # Check for harsh braking
    if acceleration_kph_s < HARSH_BRAKE_KPH_S:
        events.append({
            'event_type': 'harsh_braking',
            'timestamp': timestamp.isoformat(),
            'lat': lat,
            'lon': lon,
            'speed_kph': speed_kph,
            'acceleration_kph_s': acceleration_kph_s,
            'meta': {'threshold': HARSH_BRAKE_KPH_S}
        })
        state['harsh_brake_count'] += 1
    
    # Check for sudden acceleration
    if acceleration_kph_s > SUDDEN_ACCEL_KPH_S:
        events.append({
            'event_type': 'sudden_acceleration',
            'timestamp': timestamp.isoformat(),
            'lat': lat,
            'lon': lon,
            'speed_kph': speed_kph,
            'acceleration_kph_s': acceleration_kph_s,
            'meta': {'threshold': SUDDEN_ACCEL_KPH_S}
        })
        state['sudden_accel_count'] += 1
    
    # Check for idling
    if speed_kph == 0:
        if state['current_idle_start_ts'] is None:
            state['current_idle_start_ts'] = timestamp
        else:
            idle_time = (timestamp - state['current_idle_start_ts']).total_seconds()
            if idle_time >= IDLE_SECONDS_THRESHOLD:
                events.append({
                    'event_type': 'idling',
                    'timestamp': timestamp.isoformat(),
                    'lat': lat,
                    'lon': lon,
                    'speed_kph': speed_kph,
                    'acceleration_kph_s': acceleration_kph_s,
                    'meta': {'idle_duration_seconds': idle_time, 'threshold': IDLE_SECONDS_THRESHOLD}
                })
                state['idle_count'] += 1
                state['current_idle_start_ts'] = None  # Reset to avoid duplicate events
    else:
        # Vehicle is moving, reset idle tracking
        state['current_idle_start_ts'] = None
        state['last_non_zero_speed_ts'] = timestamp
    
    # Update state
    state['last_speed_kph'] = speed_kph
    state['last_timestamp'] = timestamp
    
    return events

def calculate_risk_score(driver_id: str) -> int:
    """Calculate risk score for a driver."""
    if driver_id not in driver_states:
        return 100  # Perfect score for new drivers
    
    state = driver_states[driver_id]
    
    # Scoring formula: max(0, 100 - (overspeed_count*2 + harsh_brake_count*3 + idle_count*1))
    penalty = (
        state['overspeed_count'] * 2 +
        state['harsh_brake_count'] * 3 +
        state['idle_count'] * 1
    )
    
    return max(0, 100 - penalty)

async def handle_point(payload: Dict, manager) -> Dict:
    """Process a GPS point and return detection results."""
    try:
        driver_id = payload['driver_id']
        timestamp = datetime.fromisoformat(payload['timestamp'].replace('Z', '+00:00'))
        lat = payload['lat']
        lon = payload['lon']
        speed_kph = payload.get('speed_kph', 0.0)
        track_id = payload.get('track_id', 'unknown')
        
        # Calculate acceleration if we have previous data
        acceleration_kph_s = 0.0
        if driver_id in driver_states:
            prev_state = driver_states[driver_id]
            acceleration_kph_s = compute_acceleration(
                prev_state['last_speed_kph'],
                prev_state['last_timestamp'],
                speed_kph,
                timestamp
            )
        
        # Detect events
        events = detect_events(driver_id, timestamp, lat, lon, speed_kph, acceleration_kph_s)
        
        # Calculate risk score
        risk_score = calculate_risk_score(driver_id)
        
        # Persist events and update scores
        if events:
            await _persist_events_and_scores(driver_id, track_id, timestamp, events, risk_score)
        
        # Prepare response
        state = driver_states[driver_id]
        result = {
            'driver_id': driver_id,
            'timestamp': timestamp.isoformat(),
            'lat': lat,
            'lon': lon,
            'speed_kph': speed_kph,
            'acceleration_kph_s': acceleration_kph_s,
            'events': events,
            'risk_score': risk_score,
            'overspeed_count': state['overspeed_count'],
            'harsh_brake_count': state['harsh_brake_count'],
            'sudden_accel_count': state['sudden_accel_count'],
            'idle_count': state['idle_count']
        }
        return result
        
    except Exception as e:
        print(f"=== Error in handle_point ===")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        # Return a minimal result to prevent simulation from stopping
        return {
            'driver_id': payload.get('driver_id', 'unknown'),
            'timestamp': payload.get('timestamp', ''),
            'lat': payload.get('lat', 0.0),
            'lon': payload.get('lon', 0.0),
            'speed_kph': payload.get('speed_kph', 0.0),
            'acceleration_kph_s': 0.0,
            'events': [],
            'risk_score': 100,
            'overspeed_count': 0,
            'harsh_brake_count': 0,
            'sudden_accel_count': 0,
            'idle_count': 0
        }

async def _persist_events_and_scores(driver_id: str, track_id: str, timestamp: datetime, events: List[Dict], risk_score: int):
    """Persist events and update driver scores."""
    from .persistence import persist_event, ensure_trip_exists, upsert_driver_score
    from .db import SessionLocal
    
    db = SessionLocal()
    try:
        # Extract numeric driver ID from string like "driver_1" -> 1
        try:
            numeric_driver_id = int(driver_id.split('_')[1])
        except (ValueError, IndexError):
            print(f"Warning: Could not parse driver_id '{driver_id}', using 1 as fallback")
            numeric_driver_id = 1
        
        # Ensure trip exists
        trip = ensure_trip_exists(db, track_id, numeric_driver_id, timestamp)
        
        # Persist each event
        for event in events:
            # Convert ISO string timestamp back to datetime for database storage
            event_timestamp = datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00'))
            
            persist_event(
                db=db,
                trip_id=trip.id,
                driver_id=numeric_driver_id,
                timestamp=event_timestamp,
                lat=event['lat'],
                lon=event['lon'],
                speed_kph=event['speed_kph'],
                acceleration_kph_s=event['acceleration_kph_s'],
                event_type=event['event_type'],
                meta=event.get('meta', {})
            )
        
        # Update driver score
        if driver_id in driver_states:
            state = driver_states[driver_id]
            upsert_driver_score(
                db=db,
                driver_id=numeric_driver_id,
                date=timestamp.date(),
                avg_speed=state.get('last_speed_kph', 0.0),
                overspeed_count=state.get('overspeed_count', 0),
                harsh_brake_count=state.get('harsh_brake_count', 0),
                idle_count=state.get('idle_count', 0),
                risk_score=risk_score
            )
    
    except Exception as e:
        print(f"Error persisting events: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

def get_driver_state(driver_id: str) -> Optional[Dict]:
    """Get current state for a driver."""
    return driver_states.get(driver_id)

def reset_driver_state(driver_id: str):
    """Reset state for a driver (useful for testing)."""
    if driver_id in driver_states:
        del driver_states[driver_id]
