from app.models.database import engine, Base

def init_db():
    """Create tables in the database if they don't exist."""
    print("🔄 Initializing Database...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database initialized successfully!")

