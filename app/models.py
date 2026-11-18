from datetime import datetime, timezone
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, UniqueConstraint, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from uuid import uuid4

def uid(): return str(uuid4())
def now(): return datetime.now(timezone.utc)
class Base(DeclarativeBase): pass
class Org(Base):
    __tablename__='orgs'
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    name: Mapped[str]=mapped_column(String(120))
class User(Base):
    __tablename__='users'
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    org_id: Mapped[str]=mapped_column(ForeignKey('orgs.id'),index=True)
    email: Mapped[str]=mapped_column(String(254),unique=True)
    password: Mapped[str]=mapped_column(String(512))
    role: Mapped[str]=mapped_column(String(20))
class Lead(Base):
    __tablename__='leads'
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    org_id: Mapped[str]=mapped_column(ForeignKey('orgs.id'),index=True)
    name: Mapped[str]=mapped_column(String(120))
    company: Mapped[str]=mapped_column(String(120))
    stage: Mapped[str]=mapped_column(String(20),default='new')
    interactions: Mapped[int]=mapped_column(Integer,default=0)
    days_since_contact: Mapped[int]=mapped_column(Integer,default=0)
    demo_requested: Mapped[bool]=mapped_column(Boolean,default=False)
    budget_confirmed: Mapped[bool]=mapped_column(Boolean,default=False)
    decision_maker: Mapped[bool]=mapped_column(Boolean,default=False)
    fit: Mapped[int]=mapped_column(Integer,default=0)
    contact_allowed: Mapped[bool]=mapped_column(Boolean,default=False)
    revision: Mapped[int]=mapped_column(Integer,default=1)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class Review(Base):
    __tablename__='reviews'
    __table_args__=(UniqueConstraint('lead_id','lead_revision',name='unique_revision_review'),)
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    org_id: Mapped[str]=mapped_column(ForeignKey('orgs.id'),index=True)
    lead_id: Mapped[str]=mapped_column(ForeignKey('leads.id'),index=True)
    lead_revision: Mapped[int]=mapped_column(Integer)
    recommendation: Mapped[str]=mapped_column(Text)
    status: Mapped[str]=mapped_column(String(20),default='pending')
    decided_by: Mapped[str|None]=mapped_column(ForeignKey('users.id'),nullable=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class Task(Base):
    __tablename__='tasks'
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    org_id: Mapped[str]=mapped_column(ForeignKey('orgs.id'),index=True)
    review_id: Mapped[str]=mapped_column(ForeignKey('reviews.id'),unique=True)
    lead_id: Mapped[str]=mapped_column(ForeignKey('leads.id'))
    title: Mapped[str]=mapped_column(Text)
    status: Mapped[str]=mapped_column(String(20),default='open')
class Audit(Base):
    __tablename__='audit'
    id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid)
    org_id: Mapped[str]=mapped_column(ForeignKey('orgs.id'),index=True)
    actor_id: Mapped[str]=mapped_column(ForeignKey('users.id'))
    action: Mapped[str]=mapped_column(String(60))
    entity_id: Mapped[str]=mapped_column(String(36))
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
