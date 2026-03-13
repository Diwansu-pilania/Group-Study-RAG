"""
FastAPI Backend — AI Learning Agent
Run from the backend/ folder with:
    cd backend
    uvicorn main:app --reload --port 8000
"""

import sys, os
# Make sure Python finds sibling modules (db, services, config)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import json

from db.models import (
    init_db, get_db, User, Roadmap, Task,
    TaskStatus, TaskType
)
from services.auth_service import (
    register_user, login_user, get_user_by_id,
    create_group, join_group, decode_token
)
from services.rag_service import (
    generate_roadmap, generate_daily_tasks, assess_submission
)
from config import get_settings
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

settings = get_settings()
app      = FastAPI(title=settings.app_name, version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    await init_db()

# ─── Auth dependency ──────────────────────────────────────────────────────────
async def get_current_user(
    authorization: str = Header(None),
    db: AsyncSession = Depends(get_db)
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token   = authorization.split(" ")[1]
    user_id = decode_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# ─── Schemas ──────────────────────────────────────────────────────────────────
class RegisterSchema(BaseModel):
    name: str; email: str; password: str; mode: str = "solo"

class LoginSchema(BaseModel):
    email: str; password: str

class GroupCreateSchema(BaseModel):
    name: str; topic: str

class GroupJoinSchema(BaseModel):
    invite_code: str

class RoadmapSchema(BaseModel):
    topic: str; goal: str
    skill_level: str = "beginner"; duration_days: int = 30

class TaskCompleteSchema(BaseModel):
    submission: str; notes: Optional[str] = None

# ─── Auth ─────────────────────────────────────────────────────────────────────
@app.post("/auth/register")
async def register(data: RegisterSchema, db: AsyncSession = Depends(get_db)):
    result = await register_user(db, data.name, data.email, data.password, data.mode)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result

@app.post("/auth/login")
async def login(data: LoginSchema, db: AsyncSession = Depends(get_db)):
    result = await login_user(db, data.email, data.password)
    if "error" in result:
        raise HTTPException(401, result["error"])
    return result

@app.get("/auth/me")
async def me(user: User = Depends(get_current_user)):
    return {"user_id": user.id, "name": user.name, "email": user.email,
            "mode": user.mode, "streak": user.streak,
            "total_xp": user.total_xp, "group_id": user.group_id}

# ─── Groups ───────────────────────────────────────────────────────────────────
@app.post("/groups/create")
async def group_create(data: GroupCreateSchema,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await create_group(db, data.name, data.topic, user.id)

@app.post("/groups/join")
async def group_join(data: GroupJoinSchema,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await join_group(db, data.invite_code, user.id)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result

# ─── Roadmap ──────────────────────────────────────────────────────────────────
@app.post("/roadmap/generate")
async def roadmap_generate(data: RoadmapSchema,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    roadmap_data = generate_roadmap(data.topic, data.goal, data.skill_level, data.duration_days)
    roadmap = Roadmap(user_id=user.id, topic=data.topic, goal=data.goal,
        skill_level=data.skill_level, duration_days=data.duration_days,
        roadmap_json=json.dumps(roadmap_data))
    db.add(roadmap); await db.commit(); await db.refresh(roadmap)
    return {"roadmap_id": roadmap.id, "roadmap": roadmap_data}

@app.post("/roadmap/{roadmap_id}/approve")
async def roadmap_approve(roadmap_id: str,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Roadmap).where(Roadmap.id == roadmap_id, Roadmap.user_id == user.id))
    roadmap = r.scalar_one_or_none()
    if not roadmap: raise HTTPException(404, "Roadmap not found")
    roadmap.approved = True; await db.commit()
    return {"status": "approved"}

@app.get("/roadmap/{user_id}/active")
async def roadmap_active(user_id: str,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Roadmap).where(
        Roadmap.user_id == user_id, Roadmap.approved == True
    ).order_by(Roadmap.created_at.desc()))
    roadmap = r.scalars().first()
    if not roadmap: return {"roadmap": None}
    return {"roadmap": json.loads(roadmap.roadmap_json),
            "roadmap_id": roadmap.id, "topic": roadmap.topic,
            "duration_days": roadmap.duration_days}

# ─── Tasks ────────────────────────────────────────────────────────────────────
@app.get("/tasks/{user_id}/today")
async def tasks_today(user_id: str,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Roadmap).where(
        Roadmap.user_id == user_id, Roadmap.approved == True
    ).order_by(Roadmap.created_at.desc()))
    roadmap = r.scalars().first()
    if not roadmap: return {"tasks": [], "day_number": 0}

    days_since = (datetime.utcnow() - roadmap.created_at).days + 1
    t = await db.execute(select(Task).where(
        Task.roadmap_id == roadmap.id, Task.day_number == days_since))
    existing = t.scalars().all()
    if existing:
        return {"tasks": [_task_dict(tk) for tk in existing], "day_number": days_since}

    roadmap_data = json.loads(roadmap.roadmap_json)
    phase_name   = _get_phase(roadmap_data, days_since)
    raw_tasks    = generate_daily_tasks(roadmap.topic, phase_name, days_since, roadmap.skill_level)

    tasks = []
    for rt in raw_tasks:
        task = Task(roadmap_id=roadmap.id, user_id=user_id, day_number=days_since,
            title=rt.get("title","Study task"), description=rt.get("description",""),
            task_type=TaskType(rt.get("task_type","read")),
            xp_reward=rt.get("xp_reward",10), due_date=datetime.utcnow())
        db.add(task); tasks.append(task)
    await db.commit()
    for task in tasks: await db.refresh(task)
    return {"tasks": [_task_dict(t) for t in tasks], "day_number": days_since}

@app.post("/tasks/{task_id}/complete")
async def task_complete(task_id: str, data: TaskCompleteSchema,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Task).where(Task.id == task_id))
    task = r.scalar_one_or_none()
    if not task: raise HTTPException(404, "Task not found")
    assessment = assess_submission(task.title, task.description, data.submission)
    task.status = TaskStatus.completed
    task.score  = assessment.get("score", 75)
    task.feedback = assessment.get("feedback","")
    task.completed_at = datetime.utcnow()
    if assessment.get("passed", True):
        user.total_xp += task.xp_reward; user.streak += 1
    await db.commit()
    return {"assessment": assessment, "xp_earned": task.xp_reward}

# ─── Progress & Leaderboard ───────────────────────────────────────────────────
@app.get("/progress/{user_id}")
async def get_progress(user_id: str,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Task).where(Task.user_id == user_id))
    tasks = r.scalars().all()
    total = len(tasks)
    done  = sum(1 for t in tasks if t.status == TaskStatus.completed)
    avg   = sum(t.score for t in tasks if t.score) / max(done, 1)
    tgt   = await get_user_by_id(db, user_id)
    return {"total_tasks": total, "completed_tasks": done,
            "completion_rate": round(done / max(total,1) * 100, 1),
            "avg_score": round(avg, 1),
            "streak": tgt.streak if tgt else 0,
            "total_xp": tgt.total_xp if tgt else 0}

@app.get("/leaderboard/{group_id}")
async def get_leaderboard(group_id: str,
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(User).where(User.group_id == group_id)
        .order_by(User.total_xp.desc()))
    members = r.scalars().all()
    return {"leaderboard": [
        {"name": m.name, "xp": m.total_xp, "streak": m.streak, "rank": i+1}
        for i, m in enumerate(members)]}

# ─── Helpers ──────────────────────────────────────────────────────────────────
def _task_dict(t):
    return {"id": t.id, "title": t.title, "description": t.description,
            "task_type": t.task_type, "status": t.status,
            "xp_reward": t.xp_reward, "day_number": t.day_number,
            "score": t.score, "feedback": t.feedback}

def _get_phase(roadmap_data, day_number):
    for phase in roadmap_data.get("phases", []):
        try:
            start, end = map(int, phase.get("days","1-7").split("-"))
            if start <= day_number <= end:
                return phase.get("phase_name","Learning")
        except Exception:
            pass
    return "Learning"