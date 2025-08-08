from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base
from .config import DATABASE_URL

engine = create_engine(DATABASE_URL, future=True)
SessionLocal = sessionmaker(bind=engine)

def init_db():
    """Initialize the database by creating all tables."""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
