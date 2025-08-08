import os
import logging
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/driverdb")

# Simulation configuration
EMIT_INTERVAL_SECONDS = float(os.getenv("EMIT_INTERVAL_SECONDS", "3.0")) 
SIMULATION_ENABLED = os.getenv("SIMULATION_ENABLED", "true").lower() == "true"

# Detection thresholds
OVERSPEED_KPH = float(os.getenv("OVERSPEED_KPH", "50"))  
HARSH_BRAKE_KPH_S = float(os.getenv("HARSH_BRAKE_KPH_S", "-5"))  
SUDDEN_ACCEL_KPH_S = float(os.getenv("SUDDEN_ACCEL_KPH_S", "5"))
IDLE_SECONDS_THRESHOLD = float(os.getenv("IDLE_SECONDS_THRESHOLD", "30"))

# Scoring configuration
SCORE_OVERSPEED_WEIGHT = int(os.getenv("SCORE_OVERSPEED_WEIGHT", "2"))
SCORE_HARSH_BRAKE_WEIGHT = int(os.getenv("SCORE_HARSH_BRAKE_WEIGHT", "3"))
SCORE_IDLE_WEIGHT = int(os.getenv("SCORE_IDLE_WEIGHT", "1"))
SCORE_BASE = int(os.getenv("SCORE_BASE", "100"))

# WebSocket configuration
WS_MAX_CONNECTIONS = int(os.getenv("WS_MAX_CONNECTIONS", "100"))
WS_HEARTBEAT_INTERVAL = int(os.getenv("WS_HEARTBEAT_INTERVAL", "30"))

# API configuration
API_RATE_LIMIT = int(os.getenv("API_RATE_LIMIT", "1000"))
API_DEFAULT_LIMIT = int(os.getenv("API_DEFAULT_LIMIT", "100"))
API_MAX_LIMIT = int(os.getenv("API_MAX_LIMIT", "1000"))

# Data paths
DATA_DIR = os.getenv("DATA_DIR", "GPS Trajectory")
TRACKS_CSV = os.path.join(DATA_DIR, "go_track_tracks.csv")
TRACKSPOINTS_CSV = os.path.join(DATA_DIR, "go_track_trackspoints.csv")

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
LOG_FILE = os.getenv("LOG_FILE", "driver_analytics.log")

# Development configuration
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
ENABLE_CORS = os.getenv("ENABLE_CORS", "true").lower() == "true"

class Config:
    """Configuration class with runtime overrides."""
    
    def __init__(self):
        self.database_url = DATABASE_URL
        self.emit_interval_seconds = EMIT_INTERVAL_SECONDS
        self.simulation_enabled = SIMULATION_ENABLED
        
        # Detection thresholds
        self.overspeed_kph = OVERSPEED_KPH
        self.harsh_brake_kph_s = HARSH_BRAKE_KPH_S
        self.sudden_accel_kph_s = SUDDEN_ACCEL_KPH_S
        self.idle_seconds_threshold = IDLE_SECONDS_THRESHOLD
        
        # Scoring weights
        self.score_overspeed_weight = SCORE_OVERSPEED_WEIGHT
        self.score_harsh_brake_weight = SCORE_HARSH_BRAKE_WEIGHT
        self.score_idle_weight = SCORE_IDLE_WEIGHT
        self.score_base = SCORE_BASE
        
        # WebSocket settings
        self.ws_max_connections = WS_MAX_CONNECTIONS
        self.ws_heartbeat_interval = WS_HEARTBEAT_INTERVAL
        
        # API settings
        self.api_rate_limit = API_RATE_LIMIT
        self.api_default_limit = API_DEFAULT_LIMIT
        self.api_max_limit = API_MAX_LIMIT
        
        # Data paths
        self.data_dir = DATA_DIR
        self.tracks_csv = TRACKS_CSV
        self.trackspoints_csv = TRACKSPOINTS_CSV
        
        # Logging
        self.log_level = LOG_LEVEL
        self.log_format = LOG_FORMAT
        self.log_file = LOG_FILE
        
        # Development
        self.debug = DEBUG
        self.enable_cors = ENABLE_CORS
    
    def update_detection_thresholds(self, 
                                  overspeed_kph: Optional[float] = None,
                                  harsh_brake_kph_s: Optional[float] = None,
                                  sudden_accel_kph_s: Optional[float] = None,
                                  idle_seconds_threshold: Optional[float] = None):
        """Update detection thresholds at runtime."""
        if overspeed_kph is not None:
            self.overspeed_kph = overspeed_kph
        if harsh_brake_kph_s is not None:
            self.harsh_brake_kph_s = harsh_brake_kph_s
        if sudden_accel_kph_s is not None:
            self.sudden_accel_kph_s = sudden_accel_kph_s
        if idle_seconds_threshold is not None:
            self.idle_seconds_threshold = idle_seconds_threshold
    
    def update_scoring_weights(self,
                             overspeed_weight: Optional[int] = None,
                             harsh_brake_weight: Optional[int] = None,
                             idle_weight: Optional[int] = None,
                             base_score: Optional[int] = None):
        """Update scoring weights at runtime."""
        if overspeed_weight is not None:
            self.score_overspeed_weight = overspeed_weight
        if harsh_brake_weight is not None:
            self.score_harsh_brake_weight = harsh_brake_weight
        if idle_weight is not None:
            self.score_idle_weight = idle_weight
        if base_score is not None:
            self.score_base = base_score
    
    def get_detection_config(self) -> dict:
        """Get detection configuration as dictionary."""
        return {
            "overspeed_kph": self.overspeed_kph,
            "harsh_brake_kph_s": self.harsh_brake_kph_s,
            "sudden_accel_kph_s": self.sudden_accel_kph_s,
            "idle_seconds_threshold": self.idle_seconds_threshold
        }
    
    def get_scoring_config(self) -> dict:
        """Get scoring configuration as dictionary."""
        return {
            "overspeed_weight": self.score_overspeed_weight,
            "harsh_brake_weight": self.score_harsh_brake_weight,
            "idle_weight": self.score_idle_weight,
            "base_score": self.score_base
        }

# Global configuration instance
config = Config()

def setup_logging():
    """Setup logging configuration."""
    logging.basicConfig(
        level=getattr(logging, config.log_level),
        format=config.log_format,
        handlers=[
            logging.FileHandler(config.log_file),
            logging.StreamHandler()
        ]
    )
    
    # Set specific logger levels
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    
    return logging.getLogger(__name__)

# Initialize logger
logger = setup_logging()
