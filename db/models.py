from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    password: str
    role: str
    full_name: str


class Bus(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    plate: str = Field(unique=True)
    model: str
    type: str
    capacity: int
    notes: Optional[str] = None


class Line(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(unique=True)
    name: str
    start_stop: str
    end_stop: str


class Assignment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    driver_id: int = Field(foreign_key="user.id")
    bus_id: int = Field(foreign_key="bus.id")
    line_id: int = Field(foreign_key="line.id")
    shift_date: date


class Incident(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    driver_id: int = Field(foreign_key="user.id")
    bus_id: Optional[int] = Field(default=None, foreign_key="bus.id")
    line_id: Optional[int] = Field(default=None, foreign_key="line.id")
    description: str
    lat: Optional[float] = None
    lon: Optional[float] = None
    photo_path: Optional[str] = None
    ai_protocol: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = "open"
