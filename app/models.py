from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

Base = declarative_base()

class Driver(Base):
    __tablename__ = "drivers"
    id = Column(Integer, primary_key=True)
    external_id = Column(String(128), unique=True, nullable=False)
    name = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Trip(Base):
    __tablename__ = "trips"
    id = Column(Integer, primary_key=True)
    track_id = Column(String(128), unique=True, nullable=False)
    driver_id = Column(Integer, ForeignKey("drivers.id"))
    start_time = Column(DateTime(timezone=True))
    end_time = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    driver = relationship("Driver")

class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True)
    trip_id = Column(Integer, ForeignKey("trips.id"))
    driver_id = Column(Integer, ForeignKey("drivers.id"))
    event_type = Column(String(64))
    timestamp = Column(DateTime(timezone=True))
    lat = Column(Float)
    lon = Column(Float)
    speed_kph = Column(Float)
    acceleration_kph_s = Column(Float)
    meta = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class DriverScore(Base):
    __tablename__ = "driver_scores"
    id = Column(Integer, primary_key=True)
    driver_id = Column(Integer, ForeignKey("drivers.id"))
    date = Column(Date)
    avg_speed = Column(Float)
    overspeed_count = Column(Integer)
    harsh_brake_count = Column(Integer)
    idle_count = Column(Integer)
    risk_score = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
