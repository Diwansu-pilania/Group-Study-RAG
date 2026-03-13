from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import random, string

from backend.db.models import User, Group, UserMode
from backend.config import get_settings

settings   = get_settings()
pwd_ctx    = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM  = "HS256"
TOKEN_EXPIRE_DAYS = 7

# ─── Password ─────────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return pwd_ctx.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_ctx.verify(plain, hashed)

# ─── JWT ──────────────────────────────────────────────────────────────────────

def create_token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(days=TOKEN_EXPIRE_DAYS)
    return jwt.encode(
        {"sub": user_id, "exp": expire},
        settings.secret_key, algorithm=ALGORITHM
    )

def decode_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None

# ─── User Operations ──────────────────────────────────────────────────────────

async def register_user(db: AsyncSession, name: str, email: str,
                        password: str, mode: str = "solo") -> dict:
    # Check email exists
    result = await db.execute(select(User).where(User.email == email))
    if result.scalar_one_or_none():
        return {"error": "Email already registered"}

    user = User(
        name=name,
        email=email,
        hashed_password=hash_password(password),
        mode=UserMode(mode)
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return {"user_id": user.id, "token": create_token(user.id)}


async def login_user(db: AsyncSession, email: str, password: str) -> dict:
    result = await db.execute(select(User).where(User.email == email))
    user   = result.scalar_one_or_none()

    if not user or not verify_password(password, user.hashed_password):
        return {"error": "Invalid email or password"}

    return {
        "user_id":  user.id,
        "name":     user.name,
        "email":    user.email,
        "mode":     user.mode,
        "streak":   user.streak,
        "total_xp": user.total_xp,
        "token":    create_token(user.id)
    }


async def get_user_by_id(db: AsyncSession, user_id: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


# ─── Group Operations ─────────────────────────────────────────────────────────

def _gen_invite_code(length=6) -> str:
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


async def create_group(db: AsyncSession, name: str, topic: str,
                       creator_id: str) -> dict:
    code  = _gen_invite_code()
    group = Group(name=name, topic=topic, invite_code=code, created_by=creator_id)
    db.add(group)
    await db.commit()
    await db.refresh(group)

    # Add creator to group
    result = await db.execute(select(User).where(User.id == creator_id))
    user   = result.scalar_one_or_none()
    if user:
        user.group_id = group.id
        user.mode     = UserMode.group
        await db.commit()

    return {"group_id": group.id, "invite_code": code}


async def join_group(db: AsyncSession, invite_code: str, user_id: str) -> dict:
    result = await db.execute(select(Group).where(Group.invite_code == invite_code))
    group  = result.scalar_one_or_none()
    if not group:
        return {"error": "Invalid invite code"}

    result = await db.execute(select(User).where(User.id == user_id))
    user   = result.scalar_one_or_none()
    if user:
        user.group_id = group.id
        user.mode     = UserMode.group
        await db.commit()

    return {"group_id": group.id, "group_name": group.name}
