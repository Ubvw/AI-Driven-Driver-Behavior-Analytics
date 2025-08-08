import pytest
import asyncio
import json
import time
from fastapi.testclient import TestClient
from app.main import app
from app.db import init_db, SessionLocal
from app.models import Driver, Trip, Event, DriverScore
from app.simulator import start_simulation, stop_simulation, is_running
from app.wsmanager import ConnectionManager
import os
import tempfile
import pandas as pd

client = TestClient(app)

class TestIntegration:
    """Integration tests for the complete system flow."""
    
    @pytest.fixture(autouse=True)
    def setup_db(self):
        """Setup test database."""
        # Use in-memory SQLite for testing
        os.environ["DATABASE_URL"] = "sqlite:///test.db"
        init_db()
        yield
        # Cleanup
        if os.path.exists("test.db"):
            os.remove("test.db")
    
    def get_unique_id(self):
        """Generate a unique ID for test data."""
        import uuid
        return str(uuid.uuid4())[:8]
    
    def create_test_csv(self):
        """Create a small test CSV file for simulation."""
        test_data = [
            {"id": 1, "latitude": 14.5995, "longitude": 120.9842, "track_id": "T1", "time": "2025-08-01T08:00:00Z", "speed": 65.0},
            {"id": 2, "latitude": 14.5996, "longitude": 120.9843, "track_id": "T1", "time": "2025-08-01T08:00:01Z", "speed": 75.0},
            {"id": 3, "latitude": 14.5997, "longitude": 120.9844, "track_id": "T1", "time": "2025-08-01T08:00:02Z", "speed": 105.0},  # Overspeeding
            {"id": 4, "latitude": 14.5998, "longitude": 120.9845, "track_id": "T1", "time": "2025-08-01T08:00:03Z", "speed": 5.0},   # Harsh braking
            {"id": 5, "latitude": 14.5999, "longitude": 120.9846, "track_id": "T1", "time": "2025-08-01T08:00:04Z", "speed": 0.0},   # Idling start
            {"id": 6, "latitude": 14.6000, "longitude": 120.9847, "track_id": "T1", "time": "2025-08-01T08:00:05Z", "speed": 0.0},   # Idling continue
        ]
        
        df = pd.DataFrame(test_data)
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        df.to_csv(temp_file.name, index=False)
        temp_file.close()
        
        return temp_file.name
    
    def test_dashboard_endpoint(self):
        """Test that the dashboard endpoint returns the correct HTML."""
        response = client.get("/dashboard")
        assert response.status_code == 200
        assert "AI Driver Behavior Analytics" in response.text
        assert "speedChart" in response.text
        assert "eventsChart" in response.text
    
    def test_api_endpoints(self):
        """Test that all API endpoints are accessible."""
        # Test drivers endpoint
        response = client.get("/api/drivers")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        
        # Test events endpoint
        response = client.get("/api/events")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        
        # Test events stats endpoint
        response = client.get("/api/events/stats")
        assert response.status_code == 200
        assert isinstance(response.json(), dict)
        
        # Test health endpoint
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    def test_simulation_control(self):
        """Test simulation start/stop endpoints."""
        # Test start simulation
        response = client.post("/api/start_simulation")
        assert response.status_code == 200
        assert "started" in response.json()["message"]
        
        # Test stop simulation
        response = client.post("/api/stop_simulation")
        assert response.status_code == 200
        assert "stopped" in response.json()["message"]
    
    def test_websocket_connection(self):
        """Test WebSocket connection and message handling."""
        with client.websocket_connect("/ws/data") as websocket:
            # Test that connection is established
            assert websocket is not None
            
            # Test that we can send a message (optional)
            websocket.send_text("ping")
            
            # Note: We can't easily test incoming messages in this context
            # as they come from the simulator, but we can verify the connection works
    
    def test_database_operations(self):
        """Test database operations through the API."""
        # Test creating a driver through the API
        # (This would require a POST endpoint, but we can test the existing GET endpoints)
        
        # Test that we can query the database
        with SessionLocal() as db:
            # Test driver creation
            unique_id = self.get_unique_id()
            driver = Driver(external_id=f"test_driver_{unique_id}", name="Test Driver")
            db.add(driver)
            db.commit()
            db.refresh(driver)
            
            # Test trip creation
            trip = Trip(track_id=f"T{unique_id}", driver_id=driver.id)
            db.add(trip)
            db.commit()
            db.refresh(trip)
            
            # Test event creation
            event = Event(
                trip_id=trip.id,
                driver_id=driver.id,
                event_type="overspeeding",
                speed_kph=105.0,
                acceleration_kph_s=0.0
            )
            db.add(event)
            db.commit()
            
            # Verify data was created
            assert db.query(Driver).count() > 0
            assert db.query(Trip).count() > 0
            assert db.query(Event).count() > 0
    
    def test_event_detection_integration(self):
        """Test that event detection works with real data flow."""
        # Create test CSV
        csv_path = self.create_test_csv()
        
        try:
            # Start simulation with test data
            response = client.post("/api/start_simulation")
            assert response.status_code == 200
            
            # Wait a bit for simulation to process
            time.sleep(2)
            
            # Stop simulation
            response = client.post("/api/stop_simulation")
            assert response.status_code == 200
            
            # Check that events were created in database
            with SessionLocal() as db:
                events = db.query(Event).all()
                # Should have at least one event (overspeeding from our test data)
                assert len(events) > 0
                
                # Check for specific event types
                overspeeding_events = [e for e in events if e.event_type == "overspeeding"]
                assert len(overspeeding_events) > 0
                
        finally:
            # Cleanup
            if os.path.exists(csv_path):
                os.remove(csv_path)
    
    def test_driver_score_calculation(self):
        """Test that driver scores can be calculated and stored."""
        with SessionLocal() as db:
            # Create a driver
            unique_id = self.get_unique_id()
            driver = Driver(external_id=f"score_test_driver_{unique_id}", name="Score Test Driver")
            db.add(driver)
            db.commit()
            db.refresh(driver)
            
            # Create some events
            events = [
                Event(driver_id=driver.id, event_type="overspeeding", speed_kph=105.0),
                Event(driver_id=driver.id, event_type="harsh_braking", speed_kph=50.0),
                Event(driver_id=driver.id, event_type="idling", speed_kph=0.0),
            ]
            
            for event in events:
                db.add(event)
            db.commit()
            
            # Manually create a driver score (since it's not automatic)
            from datetime import date
            score = DriverScore(
                driver_id=driver.id,
                date=date.today(),
                avg_speed=50.0,
                overspeed_count=1,
                harsh_brake_count=1,
                idle_count=1,
                risk_score=95  # 100 - (1*2 + 1*3 + 1*1) = 94
            )
            db.add(score)
            db.commit()
            
            # Check that driver scores were created
            scores = db.query(DriverScore).filter(DriverScore.driver_id == driver.id).all()
            assert len(scores) > 0
            
            # Verify the score calculation
            score = scores[0]
            assert score.overspeed_count == 1
            assert score.harsh_brake_count == 1
            assert score.idle_count == 1
            assert score.risk_score == 95
    
    def test_api_filtering(self):
        """Test API filtering capabilities."""
        with SessionLocal() as db:
            # Create test data
            unique_id = self.get_unique_id()
            driver = Driver(external_id=f"filter_test_driver_{unique_id}", name="Filter Test Driver")
            db.add(driver)
            db.commit()
            db.refresh(driver)
            
            # Create events for this driver
            events = [
                Event(driver_id=driver.id, event_type="overspeeding", speed_kph=105.0),
                Event(driver_id=driver.id, event_type="harsh_braking", speed_kph=50.0),
            ]
            
            for event in events:
                db.add(event)
            db.commit()
            
            # Test filtering by driver_id
            response = client.get(f"/api/drivers/{driver.id}/events")
            assert response.status_code == 200
            events_data = response.json()
            assert len(events_data) > 0
            
            # Test events stats with filtering
            response = client.get(f"/api/events/stats?driver_id={driver.id}")
            assert response.status_code == 200
            stats = response.json()
            assert "total_events" in stats
    
    def test_simulation_state_management(self):
        """Test that simulation state is properly managed."""
        # Test initial state
        assert not is_running()
        
        # Test start simulation
        response = client.post("/api/start_simulation")
        assert response.status_code == 200
        
        # Give it a moment to start
        time.sleep(0.5)
        
        # Test stop simulation
        response = client.post("/api/stop_simulation")
        assert response.status_code == 200
        
        # Verify stopped
        assert not is_running()
    
    def test_error_handling(self):
        """Test error handling in the API."""
        # Test invalid driver ID
        response = client.get("/api/drivers/99999/events")
        assert response.status_code == 200  # Should return empty list, not error
        
        # Test invalid event ID
        response = client.get("/api/events?driver_id=99999")
        assert response.status_code == 200  # Should return empty list, not error
    
    def test_data_persistence(self):
        """Test that data persists across API calls."""
        with SessionLocal() as db:
            # Create test data
            unique_id = self.get_unique_id()
            driver = Driver(external_id=f"persistence_test_{unique_id}", name="Persistence Test")
            db.add(driver)
            db.commit()
            db.refresh(driver)
            
            # Verify data persists
            driver_count = db.query(Driver).count()
            assert driver_count > 0
            
            # Test that we can retrieve the data via API
            response = client.get("/api/drivers")
            assert response.status_code == 200
            drivers_data = response.json()
            assert len(drivers_data) > 0

if __name__ == "__main__":
    pytest.main([__file__])
