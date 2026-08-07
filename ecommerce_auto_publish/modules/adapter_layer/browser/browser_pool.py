"""Browser 池管理 — 管理 Playwright 实例，支持并发和多平台"""
import asyncio
import os
import time
import hashlib
from typing import Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime

try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False
    Browser = None
    BrowserContext = None
    Page = None


@dataclass
class BrowserSession:
    """单个浏览器会话 — 一个平台一个店铺一个会话"""
    session_id: str
    platform: str
    shop_id: str
    browser: Optional[Browser] = None
    context: Optional[BrowserContext] = None
    page: Optional[Page] = None
    state_file: str = ""        # storage_state.json 持久化cookie
    status: str = "idle"        # idle / busy / login_required / error
    last_used: float = 0
    created_at: str = ""
    auto_close_at: float = 0    # 空闲超时自动关闭


class BrowserPool:
    """Playwright Browser 池 — 单例管理所有浏览器会话"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._playwright = None
        self._sessions: Dict[str, BrowserSession] = {}
        self._lock = asyncio.Lock() if HAS_PLAYWRIGHT else None
        self._data_dir = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "data", "browser_states"
        )
        os.makedirs(self._data_dir, exist_ok=True)
        self._max_idle_seconds = 600  # 10分钟空闲自动关闭
        self._cleanup_task = None
        print(f"[BrowserPool] Data dir: {self._data_dir}")

    # ---- Session Management ----

    def _session_key(self, platform: str, shop_id: str) -> str:
        return f"{platform}_{shop_id}"

    async def get_session(self, platform: str, shop_id: str = "default") -> BrowserSession:
        """获取或创建一个浏览器会话"""
        if not HAS_PLAYWRIGHT:
            raise RuntimeError("Playwright 未安装: pip install playwright && playwright install chromium")

        key = self._session_key(platform, shop_id)

        # 复用已有会话
        if key in self._sessions:
            session = self._sessions[key]
            if session.status == "error":
                # 错误状态 → 重建
                await self._destroy_session(key)
            else:
                session.last_used = time.time()
                session.status = "busy"
                return session

        # 新建会话
        session = await self._create_session(platform, shop_id)
        self._sessions[key] = session
        return session

    async def release_session(self, platform: str, shop_id: str = "default"):
        """释放会话（标记空闲）"""
        key = self._session_key(platform, shop_id)
        if key in self._sessions:
            self._sessions[key].status = "idle"
            self._sessions[key].last_used = time.time()

    async def _create_session(self, platform: str, shop_id: str) -> BrowserSession:
        """创建新浏览器会话"""
        if self._playwright is None:
            self._playwright = await async_playwright().start()

        key = self._session_key(platform, shop_id)
        session_id = hashlib.md5(key.encode()).hexdigest()[:12]
        state_file = os.path.join(self._data_dir, f"{key}_state.json")

        # 启动 Chromium
        browser = await self._playwright.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )

        # 尝试加载已有登录状态
        context_kwargs = {
            "viewport": {"width": 1366, "height": 768},
            "locale": "zh-CN",
            "timezone_id": "Asia/Shanghai",
        }

        if os.path.exists(state_file):
            try:
                context = await browser.new_context(storage_state=state_file, **context_kwargs)
                print(f"[BrowserPool] Loaded saved state for {key}")
            except Exception:
                context = await browser.new_context(**context_kwargs)
        else:
            context = await browser.new_context(**context_kwargs)

        # 注入反检测脚本
        await context.add_init_script("""
            Object.defineProperty(navigator, "webdriver", { get: () => false });
            Object.defineProperty(navigator, "plugins", { get: () => [1,2,3,4,5] });
            Object.defineProperty(navigator, "languages", { get: () => ["zh-CN","zh","en"] });
            window.chrome = { runtime: {} };
        """)

        page = await context.new_page()
        now = time.time()

        session = BrowserSession(
            session_id=session_id,
            platform=platform,
            shop_id=shop_id,
            browser=browser,
            context=context,
            page=page,
            state_file=state_file,
            status="busy",
            last_used=now,
            created_at=datetime.utcnow().isoformat(),
            auto_close_at=now + self._max_idle_seconds,
        )
        print(f"[BrowserPool] Created session {session_id} for {key}")
        return session

    # ---- State Persistence ----

    async def save_state(self, platform: str, shop_id: str = "default"):
        """保存浏览器登录状态（cookie + localStorage）"""
        key = self._session_key(platform, shop_id)
        session = self._sessions.get(key)
        if session and session.context:
            await session.context.storage_state(path=session.state_file)
            print(f"[BrowserPool] Saved state for {key} → {session.state_file}")

    # ---- Cleanup ----

    async def _destroy_session(self, key: str):
        """销毁一个会话"""
        session = self._sessions.pop(key, None)
        if session:
            try:
                if session.page:
                    await session.page.close()
            except Exception:
                pass
            try:
                if session.context:
                    await session.context.close()
            except Exception:
                pass
            try:
                if session.browser:
                    await session.browser.close()
            except Exception:
                pass
            print(f"[BrowserPool] Destroyed session {session.session_id}")

    async def close_idle_sessions(self):
        """关闭闲置过久的会话"""
        now = time.time()
        expired = [
            k for k, s in self._sessions.items()
            if s.status == "idle" and now > s.auto_close_at
        ]
        for k in expired:
            await self._destroy_session(k)
        if expired:
            print(f"[BrowserPool] Closed {len(expired)} idle sessions")

    async def shutdown(self):
        """关闭所有会话，停止 Playwright"""
        for key in list(self._sessions.keys()):
            await self._destroy_session(key)
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        print("[BrowserPool] Shutdown complete")

    def list_sessions(self) -> list:
        """列出所有会话状态"""
        return [
            {
                "session_id": s.session_id,
                "platform": s.platform,
                "shop_id": s.shop_id,
                "status": s.status,
                "has_state": os.path.exists(s.state_file),
                "last_used": s.last_used,
            }
            for s in self._sessions.values()
        ]


# 全局单例
browser_pool = BrowserPool()
print("[BrowserPool] Initialized (lazy Playwright start)")
