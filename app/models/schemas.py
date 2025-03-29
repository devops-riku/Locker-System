from typing import List
from pydantic import BaseModel, Field

class SuperAdminCreate(BaseModel):
    email: str
    password: str = Field(min_length=6)
    is_super_admin: bool = True

class UserLoginRequest(BaseModel):
    email: str = Field(...)
    password: str = Field(..., min_length=6, max_length=50)


class CreateUserRequest(BaseModel):
    first_name: str = Field(...)
    last_name: str = Field(...)
    id_number: str = Field(...)
    address: str = Field(...)
    email: str = Field(...)
    password: str = Field(...)
    locker_number: int = Field(...)
    rfid_serial_number: str = Field(...)
    pin_number: int = Field(..., ge=0000, le=9999) 


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
    email: str
    assigned_locker: int

    