from typing import List, Optional
from pydantic import BaseModel, Field


class SuperAdminCreate(BaseModel):
    email: str
    password: str = Field(..., min_length=6)
    is_super_admin: bool = True


class UserLoginRequest(BaseModel):
    email: str = Field(...)
    password: str = Field(..., max_length=50)


class CreateUserRequest(BaseModel):
    first_name: str = Field(...)
    last_name: str = Field(...)
    id_number: str = Field(...)
    address: str = Field(...)
    email: str = Field(...)
    password: str = Field(...)
    locker_number: int = Field(...)
    rfid_serial_number: str = Field(...)
    pin_number: str = Field(..., max_length=4)


class AddLockerRequest(BaseModel):
    locker_name: str = Field(...)
    relay_pin: int = Field(...)
    is_available: bool = Field(True)


class RequestEmailResetPassword(BaseModel):
    email: str = Field(...)


class AddLockerRequest(BaseModel):
    locker_name: str
    relay_pin: int


class UpdateLockerRequest(BaseModel):
    locker_name: str
    relay_pin: int
    is_available: bool = True


class UpdateUserRequest(BaseModel):
    first_name: str
    last_name: str
    id_number: str
    address: str
    assigned_locker: int
    pin_number: str = Field(None, max_length=4)
    rfid_serial_number: str = Field(None, min_length=8, max_length=12)
    is_active: bool


class HistoryLogRequest(BaseModel):
    action: str


class PinValidationRequest(BaseModel):
    pin: str


class ProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    id_number: Optional[str] = None


class PasswordUpdate(BaseModel):
    new_password: str


class PinUpdate(BaseModel):
    current_pin: str
    new_pin: str


class AddHistoryLogRequest(BaseModel):
    user_id: int
    action: str
