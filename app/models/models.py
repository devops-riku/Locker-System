from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from app.models.database import Base, engine
from datetime import datetime, timezone


class User(Base):
    __tablename__ = "users" 
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    avatar = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    id_number = Column(String, unique=True, nullable=True)
    address = Column(String, nullable=True)
    email = Column(String, unique=True, nullable=False)
    is_super_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    created_by = Column(String, nullable=True)
    
    # Relationships
    credentials = relationship("UserCredential", back_populates="user", cascade="all, delete-orphan")
    history_logs = relationship("History", back_populates="user", cascade="all, delete-orphan")

class UserCredential(Base): 
    __tablename__ = "user_credentials" 
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    locker_id = Column(Integer, ForeignKey("lockers.id", ondelete="SET NULL"), nullable=True)
    rfid_serial_number = Column(String, nullable=False)
    pin_number = Column(String, nullable=False)
    attempt_duration = Column(DateTime, nullable=True)
    is_current_holder = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="credentials")
    locker = relationship("Locker", back_populates="user_credential")

class History(Base): 
    __tablename__ = "history_logs"  

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    action = Column(String, nullable=False)
    date_created = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationship
    user = relationship("User", back_populates="history_logs")

class Locker(Base):
    __tablename__ = "lockers"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False)
    relay_pin = Column(Integer, unique=True, nullable=False)
    is_available = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    created_by = Column(String, nullable=True)

    user_credential = relationship("UserCredential", back_populates="locker", cascade="all, delete-orphan")