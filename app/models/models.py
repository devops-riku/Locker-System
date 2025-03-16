from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
import datetime
from app.models.database import Base, engine


class User(Base):
    __tablename__ = "users" 

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    is_super_admin = Column(Boolean, default=False)

    # Relationships
    credentials = relationship("UserCredential", back_populates="user", cascade="all, delete")
    unlock_histories = relationship("UnlockHistory", back_populates="user", cascade="all, delete")


class UserCredential(Base): 
    __tablename__ = "user_credentials" 

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    pin = Column(Integer, nullable=True)  # Numeric PIN (nullable)
    relay_number = Column(Integer, nullable=False)

    # Relationship
    user = relationship("User", back_populates="credentials")


class UnlockHistory(Base): 
    __tablename__ = "unlock_histories"  

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    payload = Column(JSON, nullable=False)  # Unlock attempt details
    date_created = Column(DateTime, default=datetime.UTC)

    # Relationship
    user = relationship("User", back_populates="unlock_histories")


class RFID(Base):
    __tablename__ = "rfids"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    serial_number = Column(String, unique=True, nullable=True)
    relay_number = Column(String, unique=True, nullable=True)
    value = Column(String, unique=True, nullable=True)
    