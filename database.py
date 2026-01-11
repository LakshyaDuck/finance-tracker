from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from models import Base, Category, PRESET_CATEGORIES
import os
from pathlib import Path

Path("data").mkdir(exist_ok=True)

engine = create_engine('sqlite:///data/fortuna.db', echo=False)
db_session = scoped_session(sessionmaker(bind=engine))

def init_db():
    """Create all tables and seed preset categories"""
    Base.metadata.create_all(engine)
    
    # Check if preset categories already exist
    existing = db_session.query(Category).filter_by(is_preset=1).first()
    if not existing:
        # Seed preset categories
        for name, cat_type in PRESET_CATEGORIES:
            category = Category(
                user_id=None,
                name=name,
                type=cat_type,
                is_preset=1
            )
            db_session.add(category)
        db_session.commit()

def get_db():
    """Get database session for use in routes"""
    return db_session

def close_db():
    """Close database session"""
    db_session.remove()