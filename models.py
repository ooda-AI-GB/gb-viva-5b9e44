from sqlalchemy import Column, Integer, String, Date, ForeignKey, DateTime, Boolean, Time
from sqlalchemy.orm import relationship
from database import Base
import datetime

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    full_name = Column(String)
    role = Column(String) # doctor, head, admin

class Meeting(Base):
    __tablename__ = "meetings"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    date = Column(Date)
    meeting_type = Column(String) # Department, CME, Hospital-wide

class Attendance(Base):
    __tablename__ = "attendance"
    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    status = Column(String) # Present, Absent, Excused

    meeting = relationship("Meeting")
    user = relationship("User")

class ClinicSlot(Base):
    __tablename__ = "clinic_slots"
    id = Column(Integer, primary_key=True, index=True)
    day_of_week = Column(String) # Monday, Tuesday...
    start_time = Column(String)
    end_time = Column(String)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    user = relationship("User")

class ServiceEntry(Base):
    __tablename__ = "service_entries"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, default=datetime.date.today)
    procedure_name = Column(String)
    user_id = Column(Integer, ForeignKey("users.id"))
    notes = Column(String)

    user = relationship("User")

class ResearchItem(Base):
    __tablename__ = "research_items"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    research_type = Column(String) # Publication, Presentation, Trial
    status = Column(String) # Submitted, Approved, Published
    user_id = Column(Integer, ForeignKey("users.id"))

    user = relationship("User")
