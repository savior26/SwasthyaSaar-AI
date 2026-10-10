from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=3, max_length=13)
    name: str = Field(..., min_length=1, max_length=255)

    gender: Optional[str] = None
    year_of_birth: Optional[int] = None
    medical_condition: Optional[str] = None
    allergy: Optional[str] = None
    blood_group: Optional[str] = Field(None, max_length=10)
    phone_number: Optional[str] = Field(None, max_length=20)

class UserResponse(BaseModel):
    
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=255)
    gender: Optional[str] = None
    year_of_birth: Optional[int] = None
    medical_condition: Optional[str] = None
    allergy: Optional[str] = None
    blood_group: Optional[str] = Field(None, max_length=10)
    phone_number: Optional[str] = Field(None, max_length=20)

class UserUpdate(BaseModel):
    name: str 
    medical_condition: str | None = None
    allergy: str | None = None
    blood_group: str | None = None
    year_of_birth: int | None = None
    phone_number: str | None = None
    

class UserPasswordUpdate(BaseModel):
    password: str | None = None