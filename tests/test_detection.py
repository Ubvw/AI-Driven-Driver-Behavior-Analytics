import pytest
from datetime import datetime, timedelta
from app.detection import (
    compute_acceleration,
    detect_events,
    calculate_risk_score,
    handle_point,
    reset_driver_state,
    get_driver_state
)
from app.config import (
    OVERSPEED_KPH,
    HARSH_BRAKE_KPH_S,
    SUDDEN_ACCEL_KPH_S,
    IDLE_SECONDS_THRESHOLD
)

class TestAccelerationComputation:
    """Test acceleration computation function."""
    
    def test_normal_acceleration(self):
        """Test normal acceleration calculation."""
        prev_ts = datetime(2020, 1, 1, 0, 0, 0)
        now = datetime(2020, 1, 1, 0, 0, 1)
        accel = compute_acceleration(50.0, prev_ts, 60.0, now)
        assert accel == 10.0
    
    def test_negative_acceleration(self):
        """Test deceleration calculation."""
        prev_ts = datetime(2020, 1, 1, 0, 0, 0)
        now = datetime(2020, 1, 1, 0, 0, 1)
        accel = compute_acceleration(60.0, prev_ts, 50.0, now)
        assert accel == -10.0
    
    def test_zero_delta_time(self):
        """Test handling of zero time delta."""
        ts = datetime(2020, 1, 1, 0, 0, 0)
        accel = compute_acceleration(50.0, ts, 60.0, ts)
        assert accel == 0.0
    
    def test_negative_delta_time(self):
        """Test handling of negative time delta."""
        prev_ts = datetime(2020, 1, 1, 0, 0, 1)
        now = datetime(2020, 1, 1, 0, 0, 0)
        accel = compute_acceleration(50.0, prev_ts, 60.0, now)
        assert accel == 0.0

class TestEventDetection:
    """Test event detection logic."""
    
    def setup_method(self):
        """Reset driver state before each test."""
        reset_driver_state("test_driver")
    
    def test_overspeeding_detection(self):
        """Test overspeeding event detection."""
        timestamp = datetime(2020, 1, 1, 0, 0, 0)
        speed = OVERSPEED_KPH + 10  # Above threshold
        
        events = detect_events("test_driver", timestamp, 0.0, 0.0, speed, 0.0)
        
        assert len(events) == 1
        assert events[0]['event_type'] == 'overspeeding'
        assert events[0]['speed_kph'] == speed
        assert events[0]['meta']['threshold'] == OVERSPEED_KPH
    
    def test_harsh_braking_detection(self):
        """Test harsh braking event detection."""
        timestamp = datetime(2020, 1, 1, 0, 0, 0)
        acceleration = HARSH_BRAKE_KPH_S - 5  # Below threshold
        
        events = detect_events("test_driver", timestamp, 0.0, 0.0, 50.0, acceleration)
        
        assert len(events) == 1
        assert events[0]['event_type'] == 'harsh_braking'
        assert events[0]['acceleration_kph_s'] == acceleration
        assert events[0]['meta']['threshold'] == HARSH_BRAKE_KPH_S
    
    def test_sudden_acceleration_detection(self):
        """Test sudden acceleration event detection."""
        timestamp = datetime(2020, 1, 1, 0, 0, 0)
        acceleration = SUDDEN_ACCEL_KPH_S + 5  # Above threshold
        
        events = detect_events("test_driver", timestamp, 0.0, 0.0, 50.0, acceleration)
        
        assert len(events) == 1
        assert events[0]['event_type'] == 'sudden_acceleration'
        assert events[0]['acceleration_kph_s'] == acceleration
        assert events[0]['meta']['threshold'] == SUDDEN_ACCEL_KPH_S
    
    def test_idling_detection(self):
        """Test idling event detection."""
        # First point: start idling
        start_time = datetime(2020, 1, 1, 0, 0, 0)
        events1 = detect_events("test_driver", start_time, 0.0, 0.0, 0.0, 0.0)
        assert len(events1) == 0  # No event yet
        
        # Second point: after idle threshold
        idle_time = start_time + timedelta(seconds=IDLE_SECONDS_THRESHOLD + 10)
        events2 = detect_events("test_driver", idle_time, 0.0, 0.0, 0.0, 0.0)
        
        assert len(events2) == 1
        assert events2[0]['event_type'] == 'idling'
        assert events2[0]['meta']['idle_duration_seconds'] >= IDLE_SECONDS_THRESHOLD
    
    def test_multiple_events_same_point(self):
        """Test detection of multiple events in same telemetry point."""
        timestamp = datetime(2020, 1, 1, 0, 0, 0)
        speed = OVERSPEED_KPH + 10
        acceleration = HARSH_BRAKE_KPH_S - 5
        
        events = detect_events("test_driver", timestamp, 0.0, 0.0, speed, acceleration)
        
        assert len(events) == 2
        event_types = [e['event_type'] for e in events]
        assert 'overspeeding' in event_types
        assert 'harsh_braking' in event_types
    
    def test_no_events_normal_driving(self):
        """Test that normal driving doesn't trigger events."""
        timestamp = datetime(2020, 1, 1, 0, 0, 0)
        speed = 50.0  # Normal speed
        acceleration = 2.0  # Normal acceleration
        
        events = detect_events("test_driver", timestamp, 0.0, 0.0, speed, acceleration)
        
        assert len(events) == 0

class TestRiskScoreCalculation:
    """Test risk score calculation."""
    
    def setup_method(self):
        """Reset driver state before each test."""
        reset_driver_state("test_driver")
    
    def test_perfect_score_new_driver(self):
        """Test that new drivers start with perfect score."""
        score = calculate_risk_score("new_driver")
        assert score == 100
    
    def test_score_with_overspeeding(self):
        """Test score calculation with overspeeding events."""
        # Simulate overspeeding events
        timestamp = datetime(2020, 1, 1, 0, 0, 0)
        detect_events("test_driver", timestamp, 0.0, 0.0, OVERSPEED_KPH + 10, 0.0)
        
        score = calculate_risk_score("test_driver")
        expected_score = 100 - (1 * 2)  # 1 overspeeding event * 2 penalty
        assert score == expected_score
    
    def test_score_with_harsh_braking(self):
        """Test score calculation with harsh braking events."""
        # Simulate harsh braking events
        timestamp = datetime(2020, 1, 1, 0, 0, 0)
        detect_events("test_driver", timestamp, 0.0, 0.0, 50.0, HARSH_BRAKE_KPH_S - 5)
        
        score = calculate_risk_score("test_driver")
        expected_score = 100 - (1 * 3)  # 1 harsh braking event * 3 penalty
        assert score == expected_score
    
    def test_score_with_idling(self):
        """Test score calculation with idling events."""
        # Simulate idling event
        start_time = datetime(2020, 1, 1, 0, 0, 0)
        idle_time = start_time + timedelta(seconds=IDLE_SECONDS_THRESHOLD + 10)
        detect_events("test_driver", start_time, 0.0, 0.0, 0.0, 0.0)
        detect_events("test_driver", idle_time, 0.0, 0.0, 0.0, 0.0)
        
        score = calculate_risk_score("test_driver")
        expected_score = 100 - (1 * 1)  # 1 idling event * 1 penalty
        assert score == expected_score
    
    def test_minimum_score(self):
        """Test that score doesn't go below 0."""
        # Simulate many events to drive score down
        timestamp = datetime(2020, 1, 1, 0, 0, 0)
        for _ in range(50):  # 50 overspeeding events
            detect_events("test_driver", timestamp, 0.0, 0.0, OVERSPEED_KPH + 10, 0.0)
        
        score = calculate_risk_score("test_driver")
        assert score == 0  # Minimum score

class TestHandlePoint:
    """Test the main handle_point function."""
    
    def setup_method(self):
        """Reset driver state before each test."""
        reset_driver_state("test_driver")
    
    def test_handle_point_basic(self):
        """Test basic point handling."""
        payload = {
            'driver_id': 'test_driver',
            'timestamp': '2020-01-01T00:00:00Z',
            'lat': 40.0,
            'lon': -74.0,
            'speed_kph': 60.0
        }
        
        result = handle_point(payload, None)  # manager not needed for this test
        
        assert result['driver_id'] == 'test_driver'
        assert result['speed_kph'] == 60.0
        assert result['lat'] == 40.0
        assert result['lon'] == -74.0
        assert 'risk_score' in result
        assert 'events' in result
    
    def test_handle_point_with_event(self):
        """Test point handling that triggers an event."""
        payload = {
            'driver_id': 'test_driver',
            'timestamp': '2020-01-01T00:00:00Z',
            'lat': 40.0,
            'lon': -74.0,
            'speed_kph': OVERSPEED_KPH + 10
        }
        
        result = handle_point(payload, None)
        
        assert len(result['events']) == 1
        assert result['events'][0]['event_type'] == 'overspeeding'
        assert result['risk_score'] < 100  # Score should be reduced

class TestDriverState:
    """Test driver state management."""
    
    def test_get_driver_state_nonexistent(self):
        """Test getting state for non-existent driver."""
        state = get_driver_state("nonexistent")
        assert state is None
    
    def test_reset_driver_state(self):
        """Test resetting driver state."""
        # Create some state
        detect_events("test_driver", datetime(2020, 1, 1, 0, 0, 0), 0.0, 0.0, 50.0, 0.0)
        
        # Verify state exists
        state = get_driver_state("test_driver")
        assert state is not None
        
        # Reset state
        reset_driver_state("test_driver")
        
        # Verify state is gone
        state = get_driver_state("test_driver")
        assert state is None
