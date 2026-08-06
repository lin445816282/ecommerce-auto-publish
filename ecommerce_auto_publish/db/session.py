"""数据库 & Redis 连接管理"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config.settings import DATABASE_URL, REDIS_URL

engine = None
SessionLocal = None
redis_client = None

def _get_engine():
    global engine, SessionLocal
    if engine is None:
        engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=10, max_overflow=20)
        SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return engine

def _get_redis():
    global redis_client
    if redis_client is None:
        try:
            import redis
            redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        except Exception:
            print("[Redis] 未连接(开发模式)")
    return redis_client

def get_db():
    """FastAPI依赖注入"""
    db = SessionLocal() if SessionLocal else None
    if db is None:
        _get_engine()
        db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """建表"""
    try:
        from db.models import Base
        engine = _get_engine()
        Base.metadata.create_all(bind=engine)
        print("[DB] All tables created.")
        return True
    except Exception as e:
        print(f"[DB] 数据库不可用(开发模式): {e}")
        return False
