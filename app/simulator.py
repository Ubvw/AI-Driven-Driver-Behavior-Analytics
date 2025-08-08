import asyncio
import pandas as pd
import math
from datetime import datetime
from typing import Optional
from .config import TRACKSPOINTS_CSV, EMIT_INTERVAL_SECONDS
from .wsmanager import ConnectionManager
from .db import SessionLocal
from .models import Driver, Trip
import traceback
from .detection import handle_point

# Global state
RUNNING = False
current_task: Optional[asyncio.Task] = None

def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two GPS points in kilometers using Haversine formula."""
    R = 6371  # Earth's radius in kilometers
    
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c

def calculate_speed_kph(lat1, lon1, time1, lat2, lon2, time2):
    """Calculate speed in km/h between two GPS points."""
    # Calculate distance in kilometers
    distance_km = calculate_distance(lat1, lon1, lat2, lon2)
    
    # Calculate time difference in hours
    time_diff_hours = (time2 - time1).total_seconds() / 3600
    
    # Avoid division by zero
    if time_diff_hours <= 0:
        return 0.0
    
    # Calculate speed in km/h
    speed_kph = distance_km / time_diff_hours
    
    return speed_kph

async def start_simulation(manager: ConnectionManager, csv_path: str = None, interval: float = None, driver_id: str = None):
    """Start the GPS simulation."""
    global RUNNING, current_task
    
    if RUNNING:
        print("=== Simulation already running ===")
        return
    
    print("=== Starting Simulation ===")
    RUNNING = True
    
    # Use default path if not provided
    if csv_path is None:
        csv_path = TRACKSPOINTS_CSV
    
    # Use default interval if not provided
    if interval is None:
        interval = EMIT_INTERVAL_SECONDS
    
    print(f"=== Simulation Debug Info ===")
    print(f"CSV Path: {csv_path}")
    print(f"Interval: {interval} seconds")
    print(f"Selected Driver ID: {driver_id}")
    
    try:
        # Start simulation in background
        current_task = asyncio.create_task(_run_simulation(manager, csv_path, interval, driver_id))
        await current_task
    except Exception as e:
        print(f"=== Simulation Error ===")
        print(f"Error: {e}")
        traceback.print_exc()
        RUNNING = False
    finally:
        print("=== Simulation Task Completed ===")
        RUNNING = False

def stop_simulation():
    """Stop the GPS simulation."""
    global RUNNING, current_task
    
    print("=== Stopping Simulation ===")
    RUNNING = False
    
    if current_task and not current_task.done():
        print("=== Cancelling current task ===")
        current_task.cancel()
    
    return {"message": "simulation stopped"}

def is_running():
    """Check if simulation is currently running."""
    return RUNNING

async def _run_simulation(manager: ConnectionManager, csv_path: str, interval: float, selected_driver_id: str = None):
    """Internal simulation runner."""
    global RUNNING
    
    print(f"=== _run_simulation started ===")
    print(f"RUNNING flag: {RUNNING}")
    
    try:
        # Read CSV data
        print("=== Reading CSV data ===")
        df = pd.read_csv(csv_path)
        df['time'] = pd.to_datetime(df['time'])
        df = df.sort_values(['track_id', 'time'])
        
        print(f"=== Data Loaded ===")
        print(f"Total data points: {len(df)}")
        print(f"Available track_ids: {sorted(df['track_id'].unique())}")
        
        # Filter by selected driver if provided
        if selected_driver_id:
            print(f"=== Filtering for driver {selected_driver_id} ===")
            # Map driver_id to track_id (assuming driver_1 = track 1, etc.)
            try:
                track_id = int(selected_driver_id.split('_')[1])
                df = df[df['track_id'] == track_id]
                print(f"Filtered data points: {len(df)}")
                unique_tracks = [track_id]
            except ValueError:
                print(f"Invalid driver_id format: {selected_driver_id}")
                RUNNING = False
                return
        else:
            # Use first 3 tracks as default
            unique_tracks = sorted(df['track_id'].unique())[:3]
            print(f"=== Using tracks: {unique_tracks} ===")
        
        # Process each track
        for track_id in unique_tracks:
            if not RUNNING:
                print(f"=== Simulation stopped by user for track {track_id} ===")
                break
                
            print(f"=== Processing track {track_id} ===")
            group = df[df['track_id'] == track_id].copy()
            group = group.sort_values('time')
            
            print(f"Selected track {track_id} with {len(group)} points")
            print(f"Time range: {group['time'].min()} to {group['time'].max()}")
            print(f"Estimated duration: {len(group) * interval:.1f} seconds ({len(group) * interval / 60:.1f} minutes)")
            
            # Ensure driver exists in DB
            driver_external_id = f"driver_{track_id}"
            db = SessionLocal()
            try:
                driver = db.query(Driver).filter(Driver.external_id == driver_external_id).first()
                if not driver:
                    print(f"Creating driver {driver_external_id}")
                    driver = Driver(external_id=driver_external_id, name=f"Driver {track_id}")
                    db.add(driver)
                    db.commit()
                    db.refresh(driver)
                
                # Ensure trip exists
                trip = db.query(Trip).filter(Trip.track_id == str(track_id)).first()
                if not trip:
                    print(f"Creating trip for track {track_id}")
                    trip = Trip(
                        track_id=str(track_id),
                        driver_id=driver.id,
                        start_time=group['time'].min(),
                        end_time=group['time'].max()
                    )
                    db.add(trip)
                    db.commit()
                    db.refresh(trip)
                
                print(f"Driver ID: {driver.id}, Trip ID: {trip.id}")
                
            except Exception as e:
                print(f"=== Database Error for track {track_id} ===")
                print(f"Error: {e}")
                traceback.print_exc()
                continue
            finally:
                db.close()
            
            # Process each point in the track
            point_count = 0
            prev_lat = None
            prev_lon = None
            prev_time = None
            
            for _, row in group.iterrows():
                if not RUNNING:
                    print(f"=== Simulation stopped by user for track {track_id} ===")
                    break
                
                point_count += 1
                current_lat = float(row['latitude'])
                current_lon = float(row['longitude'])
                current_time = row['time']
                
                # Calculate speed from GPS coordinates
                speed_kph = 0.0
                if prev_lat is not None and prev_lon is not None and prev_time is not None:
                    speed_kph = calculate_speed_kph(
                        prev_lat, prev_lon, prev_time,
                        current_lat, current_lon, current_time
                    )
                
                # Create telemetry payload
                telemetry_payload = {
                    "driver_id": driver_external_id,
                    "track_id": str(track_id),
                    "timestamp": current_time.isoformat(),
                    "lat": current_lat,
                    "lon": current_lon,
                    "speed_kph": speed_kph
                }
                
                # Create WebSocket broadcast payload
                ws_payload = {
                    "type": "telemetry",
                    "payload": telemetry_payload
                }
                
                # Debug logging every 10 points
                if point_count % 10 == 0:
                    print(f"Processed {point_count}/{len(group)} points for track {track_id} ({point_count/len(group)*100:.1f}%)")
                    print(f"  Current time: {current_time}")
                    print(f"  Speed: {speed_kph:.1f} km/h")
                    print(f"  RUNNING flag: {RUNNING}")
                
                try:
                    # Process through detection pipeline
                    detection_result = await handle_point(telemetry_payload, manager)
                    
                    # Broadcast telemetry to WebSocket
                    if manager and manager.active_connections:
                        await manager.broadcast(ws_payload)
                        print(f"  ✓ Broadcasted telemetry point {point_count} to {len(manager.active_connections)} connections")
                        
                        # Broadcast score update if available
                        if detection_result and 'risk_score' in detection_result:
                            score_payload = {
                                "type": "score",
                                "payload": {
                                    "driver_id": detection_result['driver_id'],
                                    "risk_score": detection_result['risk_score'],
                                    "overspeed_count": detection_result.get('overspeed_count', 0),
                                    "harsh_brake_count": detection_result.get('harsh_brake_count', 0),
                                    "sudden_accel_count": detection_result.get('sudden_accel_count', 0),
                                    "idle_count": detection_result.get('idle_count', 0)
                                }
                            }
                            await manager.broadcast(score_payload)
                            print(f"  ✓ Broadcasted score update: {detection_result['risk_score']}")
                        
                        # Broadcast events if any detected
                        if detection_result and detection_result.get('events'):
                            for event in detection_result['events']:
                                event_payload = {
                                    "type": "event",
                                    "payload": event
                                }
                                await manager.broadcast(event_payload)
                                print(f"  ✓ Broadcasted event: {event['event_type']}")
                    else:
                        print(f"  ⚠️ No active WebSocket connections")
                    
                except Exception as e:
                    print(f"=== Error processing point {point_count} ===")
                    print(f"Error: {e}")
                    traceback.print_exc()
                    # Continue with next point instead of stopping
                    continue
                
                # Update previous values for next iteration
                prev_lat = current_lat
                prev_lon = current_lon
                prev_time = current_time
                
                # Sleep between points
                try:
                    await asyncio.sleep(interval)
                except Exception as e:
                    print(f"=== Error during sleep ===")
                    print(f"Error: {e}")
                    traceback.print_exc()
                    break
            
            print(f"Completed track {track_id} - processed all {len(group)} points")
        
        print("=== Simulation completed - all tracks processed ===")
        
    except Exception as e:
        print(f"=== Fatal simulation error ===")
        print(f"Error: {e}")
        traceback.print_exc()
    finally:
        print("=== _run_simulation ending ===")
        RUNNING = False

async def _ensure_driver_exists(track_id: str) -> int:
    """Ensure driver exists in database and return driver_id."""
    db = SessionLocal()
    try:
        # Create a synthetic driver ID based on track_id
        external_id = f"driver_{track_id}"
        
        # Check if driver exists
        driver = db.query(Driver).filter(Driver.external_id == external_id).first()
        
        if not driver:
            # Create new driver
            driver = Driver(
                external_id=external_id,
                name=f"Driver {track_id}"
            )
            db.add(driver)
            db.commit()
            db.refresh(driver)
        
        return driver.id
        
    except Exception as e:
        print(f"Error ensuring driver exists: {e}")
        return 1  # Fallback driver ID
    finally:
        db.close()
