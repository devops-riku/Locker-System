from pydantic import BaseModel, Field


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

