import os
from datetime import date, datetime, timedelta, timezone

import jwt
import psycopg
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from pwdlib import PasswordHash

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://social:social@localhost:5432/social")
JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production")
password_hash = PasswordHash.recommended()
security = HTTPBearer()
app = FastAPI(title="Highload homework: social network")


class UserCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    birth_date: date
    gender: str = Field(min_length=1, max_length=30)
    interests: str = Field(default="", max_length=2000)
    city: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    user_id: int
    password: str


def connection():
    return psycopg.connect(DATABASE_URL)


def token_for(user_id: int) -> str:
    payload = {"sub": str(user_id), "exp": datetime.now(timezone.utc) + timedelta(hours=12)}
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> int:
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=["HS256"])
        return int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc


@app.get("/health")
def health():
    with connection() as conn:
        conn.execute("SELECT 1")
    return {"status": "ok"}


@app.post("/user/register", status_code=201)
def register(user: UserCreate):
    hashed = password_hash.hash(user.password)
    query = """
        INSERT INTO users
          (first_name, last_name, birth_date, gender, interests, city, password_hash)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """
    try:
        with connection() as conn:
            row = conn.execute(query, (user.first_name, user.last_name, user.birth_date,
                                       user.gender, user.interests, user.city, hashed)).fetchone()
            conn.commit()
    except psycopg.errors.UniqueViolation as exc:
        raise HTTPException(status_code=409, detail="User already exists") from exc
    return {"id": row[0]}


@app.post("/login")
def login(data: LoginRequest):
    with connection() as conn:
        row = conn.execute("SELECT password_hash FROM users WHERE id = %s", (data.user_id,)).fetchone()
    if not row or not password_hash.verify(data.password, row[0]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"access_token": token_for(data.user_id), "token_type": "bearer"}


@app.get("/user/get/{user_id}")
def get_user(user_id: int, _: int = Depends(current_user)):
    with connection() as conn:
        row = conn.execute("""
            SELECT id, first_name, last_name, birth_date, gender, interests, city
            FROM users WHERE id = %s
        """, (user_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return {"id": row[0], "first_name": row[1], "last_name": row[2],
            "birth_date": row[3], "gender": row[4], "interests": row[5], "city": row[6]}

