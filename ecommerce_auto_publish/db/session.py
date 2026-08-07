"""数据库 & Redis 连接管理 — 自动适配SQLite/MySQL"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config.settings import DATABASE_URL, REDIS_URL

# 检测数据库类型
IS_SQLITE = "sqlite" in DATABASE_URL

if IS_SQLITE:
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=10, max_overflow=20)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# Redis（可选用）
redis_client = None
try:
    import redis
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    redis_client.ping()
    print("[Redis] Connected.")
except Exception:
    print("[Redis] Not available (dev mode).")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    from db.models import Base
    Base.metadata.create_all(bind=engine)
    print("[DB] Tables created.")

print(f"[DB] Engaged: {'SQLite' if IS_SQLITE else 'MySQL'}")
