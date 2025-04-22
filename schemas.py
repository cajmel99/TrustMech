from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime, date, time

class UserCreate(BaseModel):
    name: str
    surname: str
    email: EmailStr
    phone: Optional[int] = None
    password: str
    role: str

class UserOut(BaseModel):
    id: int
    email: EmailStr

class MechanicCreate(BaseModel):
    user_id: int
    name: str
    address: str
    city: str

class MechanicOut(BaseModel):
    id: int
    name: str
    city: str
    address: str
    rating: Optional[float] = None

class MechanicRegister(BaseModel):
    name: str
    surname: str
    email: EmailStr
    phone: Optional[int]
    password: str
    garage_name: str
    address: str
    city: str

class ServiceCreate(BaseModel):
    name: str
    price: int
    duration: time  # Format: "01:30:00"

class ServiceOut(BaseModel):
    id: int
    name: str
    price: int
    duration: time

    class Config:
        orm_mode = True

class TimeSlotCreate(BaseModel):
    date: date
    start_time: datetime
    end_time: datetime
    service_id: Optional[int] = None  # ✅ This makes it nullable


class AppointmentCreate(BaseModel):
    client_id: int
    mechanic_id: int
    service_id: int
    time_slot_id: int
