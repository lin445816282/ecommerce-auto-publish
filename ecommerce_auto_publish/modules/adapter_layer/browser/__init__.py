"""Browser automation layer — Playwright-based platform adapters

Usage:
    from modules.adapter_layer.browser import get_browser_adapter

    adapter = get_browser_adapter("taobao", shop_config)
    result = await adapter.full_pipeline_async(product)
"""
from .browser_pool import browser_pool, BrowserSession
from .browser_base import BrowserPlatformAdapter, PLATFORM_URLS

_adapters = {}


def get_browser_adapter(platform: str, shop_config: dict = None):
    """获取浏览器自动化适配器实例"""
    shop_config = shop_config or {}
    platform = platform.lower()

    if platform not in _adapters:
        if platform == "taobao":
            from .taobao_browser import TaobaoBrowserAdapter
            _adapters[platform] = TaobaoBrowserAdapter
        elif platform == "douyin":
            from .douyin_browser import DouyinBrowserAdapter
            _adapters[platform] = DouyinBrowserAdapter
        elif platform in ("pdd", "pinduoduo"):
            from .pdd_browser import PDDBrowserAdapter
            _adapters[platform] = PDDBrowserAdapter
        elif platform == "amazon":
            from .amazon_browser import AmazonBrowserAdapter
            _adapters[platform] = AmazonBrowserAdapter
        else:
            raise ValueError(f"Unknown platform: {platform}")

    adapter_cls = _adapters[platform]
    return adapter_cls(shop_config)


__all__ = [
    "browser_pool",
    "BrowserSession",
    "BrowserPlatformAdapter",
    "PLATFORM_URLS",
    "get_browser_adapter",
]
