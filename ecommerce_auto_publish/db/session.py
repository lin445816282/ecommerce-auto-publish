"""数据库 & Redis 连接管理"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import redis
from config.settings import DATABASE_URL, REDIS_URL

engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=10, max_overflow=20)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

redis_client = redis.from_url(REDIS_URL, decode_responses=True)

def get_db():
    """FastAPI依赖注入"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """建表"""
    from db.models import Base
    Base.metadata.create_all(bind=engine)
    print("[DB] All tables created.")

print("[DB] Session & Redis ready.")
