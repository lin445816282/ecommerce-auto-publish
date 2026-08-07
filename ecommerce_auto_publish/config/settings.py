"""全局配置"""
import os

# 数据库 — 开发模式自动切换SQLite
DB_URL = os.getenv("DB_URL", "")
if DB_URL:
    DATABASE_URL = DB_URL
else:
    DB_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(DB_DIR, exist_ok=True)
    DATABASE_URL = f"sqlite:///{os.path.join(DB_DIR, 'ecommerce.db')}"

# Redis — 开发模式可选
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# 环境
ENV = os.getenv("ENV", "dev")

# API密钥（加密存储）
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-in-production")

# 限流参数
RATE_LIMIT_QPS = int(os.getenv("RATE_LIMIT_QPS", "10"))
DAILY_LIMIT = int(os.getenv("DAILY_LIMIT", "5000"))

# AI配置
AI_PROVIDER = os.getenv("AI_PROVIDER", "openai")  # openai / claude
AI_API_KEY = os.getenv("AI_API_KEY", "")
AI_MODEL = os.getenv("AI_MODEL", "gpt-4")

# 重试配置
MAX_RETRY = 3
RETRY_DELAY = [2, 5, 15]  # 指数退避秒数

# 熔断
CIRCUIT_BREAKER_THRESHOLD = 10  # 连续失败次数
CIRCUIT_BREAKER_TIMEOUT = 300   # 熔断恢复时间(秒)

# 文件路径
BAN_WORD_FILE = os.path.join(os.path.dirname(__file__), "..", "utils", "ban_word.txt")
PLATFORM_CONFIG = os.path.join(os.path.dirname(__file__), "platform_adapter.yaml")

print(f"[Config] Database: {DATABASE_URL}")
