from sqlalchemy import (
    Column, String, Integer, Float, Boolean,
    DateTime, Text, ForeignKey, Enum
)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from datetime import datetime
import uuid, enum
from backend.config import get_settings

settings = get_settings()
Base = declarative_base()

# ─── Enums ────────────────────────────────────────────────────────────────────

class UserMode(str, enum.Enum):
    solo  = "solo"
    group = "group"

class TaskType(str, enum.Enum):
    read    = "read"
    quiz    = "quiz"
    project = "project"
    video   = "video"

class TaskStatus(str, enum.Enum):
    pending    = "pending"
    completed  = "completed"
    skipped    = "skipped"

# ─── Models ───────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"
    id            = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name          = Column(String(100), nullable=False)
    email         = Column(String(200), unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    mode          = Column(Enum(UserMode), default=UserMode.solo)
    group_id      = Column(String, ForeignKey("groups.id"), nullable=True)
    created_at    = Column(DateTime, default=datetime.utcnow)
    streak        = Column(Integer, default=0)
    total_xp      = Column(Integer, default=0)

    roadmaps      = relationship("Roadmap",  back_populates="user")
    tasks         = relationship("Task",     back_populates="user")
    group         = relationship("Group",    back_populates="members")


class Group(Base):
    __tablename__ = "groups"
    id            = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name          = Column(String(100), nullable=False)
    invite_code   = Column(String(10), unique=True, nullable=False)
    created_by    = Column(String, ForeignKey("users.id"))
    created_at    = Column(DateTime, default=datetime.utcnow)
    topic         = Column(String(200))

    members       = relationship("User",  back_populates="group")


class Roadmap(Base):
    __tablename__ = "roadmaps"
    id            = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id       = Column(String, ForeignKey("users.id"), nullable=False)
    topic         = Column(String(200), nullable=False)
    goal          = Column(Text)
    skill_level   = Column(String(50))          # beginner / intermediate / advanced
    duration_days = Column(Integer, default=30)
    roadmap_json  = Column(Text)                # full JSON from LLM
    approved      = Column(Boolean, default=False)
    created_at    = Column(DateTime, default=datetime.utcnow)
    completed_at  = Column(DateTime, nullable=True)

    user          = relationship("User", back_populates="roadmaps")
    tasks         = relationship("Task", back_populates="roadmap")


class Task(Base):
    __tablename__ = "tasks"
    id            = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    roadmap_id    = Column(String, ForeignKey("roadmaps.id"), nullable=False)
    user_id       = Column(String, ForeignKey("users.id"),    nullable=False)
    day_number    = Column(Integer, nullable=False)
    title         = Column(String(300), nullable=False)
    description   = Column(Text)
    task_type     = Column(Enum(TaskType), default=TaskType.read)
    status        = Column(Enum(TaskStatus), default=TaskStatus.pending)
    score         = Column(Float, nullable=True)
    feedback      = Column(Text, nullable=True)
    due_date      = Column(DateTime, nullable=True)
    completed_at  = Column(DateTime, nullable=True)
    xp_reward     = Column(Integer, default=10)

    roadmap       = relationship("Roadmap", back_populates="tasks")
    user          = relationship("User",    back_populates="tasks")


class DailyProgress(Base):
    __tablename__ = "daily_progress"
    id            = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id       = Column(String, ForeignKey("users.id"), nullable=False)
    date          = Column(DateTime, default=datetime.utcnow)
    tasks_done    = Column(Integer, default=0)
    tasks_total   = Column(Integer, default=0)
    xp_earned     = Column(Integer, default=0)
    streak_day    = Column(Integer, default=0)

# ─── Engine & Session ─────────────────────────────────────────────────────────

engine = create_async_engine(settings.database_url, echo=settings.debug)

AsyncSessionLocal = sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database initialized")

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
