import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_dashboard_page_loads():
    """Test that the dashboard page loads successfully."""
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "AI Driver Behavior Analytics" in response.text
    assert "driver-selector" in response.text
    assert "speedChart" in response.text
    assert "eventsChart" in response.text

def test_dashboard_has_driver_selector():
    """Test that the dashboard includes the driver selector dropdown."""
    response = client.get("/dashboard")
    assert "driverSelect" in response.text
    assert "All Drivers" in response.text

def test_dashboard_has_enhanced_ui_elements():
    """Test that the dashboard includes the new UI enhancements."""
    response = client.get("/dashboard")
    
    # Check for new UI elements
    assert "stats-grid" in response.text
    assert "score-container" in response.text
    assert "event-indicators" in response.text
    
    # Check for specific stat cards
    assert "Total Events" in response.text
    assert "Avg Speed" in response.text
    assert "Max Speed" in response.text
    assert "Active Drivers" in response.text

def test_dashboard_has_event_indicators():
    """Test that the dashboard includes event indicators."""
    response = client.get("/dashboard")
    
    # Check for event indicators
    assert "overspeeding-indicator" in response.text
    assert "harsh-braking-indicator" in response.text
    assert "sudden-acceleration-indicator" in response.text
    assert "idling-indicator" in response.text

def test_dashboard_has_enhanced_charts():
    """Test that the dashboard includes enhanced chart configurations."""
    response = client.get("/dashboard")
    
    # Check for enhanced chart features
    assert "maintainAspectRatio: false" in response.text
    assert "animation:" in response.text
    assert "easeInOutQuart" in response.text

def test_dashboard_has_modern_styling():
    """Test that the dashboard includes modern CSS styling."""
    response = client.get("/dashboard")
    
    # Check for modern styling elements
    assert "linear-gradient" in response.text
    assert "border-radius: 12px" in response.text
    assert "box-shadow" in response.text
    assert "transition" in response.text

def test_dashboard_has_emoji_icons():
    """Test that the dashboard includes emoji icons for better UX."""
    response = client.get("/dashboard")
    
    # Check for emoji icons
    assert "🚗" in response.text  # Header
    assert "📈" in response.text  # Speed chart
    assert "📊" in response.text  # Events chart
    assert "🎯" in response.text  # Risk score
    assert "▶️" in response.text  # Start button
    assert "⏹️" in response.text  # Stop button

def test_dashboard_has_websocket_connection():
    """Test that the dashboard includes WebSocket connection logic."""
    response = client.get("/dashboard")
    
    # Check for WebSocket functionality
    assert "WebSocket" in response.text
    assert "connectWebSocket" in response.text
    assert "onmessage" in response.text
    assert "wsUrl" in response.text

def test_dashboard_has_driver_filtering():
    """Test that the dashboard includes driver filtering functionality."""
    response = client.get("/dashboard")
    
    # Check for driver filtering logic
    assert "selectedDriver" in response.text
    assert "loadDrivers" in response.text
    assert "driverSelect" in response.text

if __name__ == "__main__":
    pytest.main([__file__])
