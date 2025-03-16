from pydantic import BaseModel, Field


class UserLoginRequest(BaseModel):
    email: str = Field(...)
    password: str = Field(..., min_length=6, max_length=50)


class UserRegisterRequest(BaseModel):
    first_name: str = Field(...)
    last_name: str = Field(...)
    email: str = Field(...)
    password: str = Field(...)
    uid: str = Field(...)
    pin: int = Field(..., min_length=4, max_digits=9999)
