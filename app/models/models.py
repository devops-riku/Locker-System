from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
import datetime
from app.models.database import Base, engine
from datetime import datetime, timezone

class User(Base):
    __tablename__ = "users" 
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    id_number = Column(String, unique=True, nullable=False)
    address = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    is_super_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    created_by = Column(String, nullable=True)
    

    # Relationships
    credentials = relationship("UserCredential", back_populates="user", cascade="all, delete")
    history_logs = relationship("History", back_populates="user", cascade="all, delete")


class UserCredential(Base): 
    __tablename__ = "user_credentials" 

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    locker_id = Column(Integer, ForeignKey("lockers.id", ondelete="CASCADE"), nullable=False)
    rfid_serial_number = Column(String, nullable=False)  # RFID card serial number
    pin_number = Column(Integer, nullable=False)  # Numeric PIN (nullable)
    is_current_holder = Column(Boolean, default=True)  # Is this the user's current locker
    created_at = Column(DateTime, default=datetime.now(timezone.utc))   # When the credential was created

    # Relationship
    user = relationship("User", back_populates="credentials")
    locker = relationship("Locker", back_populates="user_credential")


class History(Base): 
    __tablename__ = "history_logs"  

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    payload = Column(JSON, nullable=False)  # Unlock attempt details
    date_created = Column(DateTime, default=datetime.now(timezone.utc))

    # Relationship
    user = relationship("User", back_populates="history_logs")


class Locker(Base):
    __tablename__ = "lockers"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False)
    relay_pin = Column(Integer, unique=True, nullable=False)
    is_available = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    created_by = Column(String, nullable=True)

    user_credential = relationship("UserCredential", back_populates="locker")
