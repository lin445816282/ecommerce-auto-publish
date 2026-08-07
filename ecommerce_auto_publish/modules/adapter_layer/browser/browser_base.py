import os, asyncio
from typing import Dict, List, Any, Optional, Tuple
from abc import ABC, abstractmethod

from .browser_pool import browser_pool, BrowserSession

PLATFORM_URLS = {
    "taobao": {
        "login": "https://login.taobao.com/member/login.jhtml",
        "seller_center": "https://myseller.taobao.com/home.htm",
        "publish": "https://myseller.taobao.com/app.htm#/product/publish",
        "draft_list": "https://myseller.taobao.com/app.htm#/product/draftList",
    },
    "douyin": {
        "login": "https://fxg.jinritemai.com/login",
        "publish": "https://fxg.jinritemai.com/ffa/merchant/product/publish",
    },
    "pdd": {
        "login": "https://mms.pinduoduo.com/login",
        "publish": "https://mms.pinduoduo.com/goods/publish",
    },
    "amazon": {
        "login": "https://sellercentral.amazon.com/",
        "publish": "https://sellercentral.amazon.com/product-dashboard",
    },
}


class BrowserPlatformAdapter(ABC):
    """浏览器自动化平台适配器基类"""

    def __init__(self, shop_config):
        self.shop_cfg = shop_config
        cls_name = self.__class__.__name__
        self.platform_name = cls_name.replace("Browser", "").replace("Adapter", "").lower()
        self.shop_id = shop_config.get("shop_id", "default")
        self.session = None
        self.page = None
        out_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "screenshots")
        os.makedirs(out_dir, exist_ok=True)
        self._shots_dir = out_dir

    @property
    def platform(self):
        return self.platform_name

    def full_pipeline(self, master_data) -> Dict[str, Any]:
        """同步包装 — 兼容 Orchestrator 的 sync 调用"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    fut = pool.submit(asyncio.run, self.full_pipeline_async(master_data))
                    return fut.result(timeout=300)
            return asyncio.run(self.full_pipeline_async(master_data))
        except RuntimeError:
            return asyncio.run(self.full_pipeline_async(master_data))

    async def init_session(self):
        try:
            self.session = await browser_pool.get_session(self.platform, self.shop_id)
            self.page = self.session.page
            return True
        except Exception as e:
            print(f"[{self.platform}] Session init failed: {e}")
            return False

    async def release(self):
        if self.session:
            await browser_pool.release_session(self.platform, self.shop_id)
        self.session = None
        self.page = None

    @abstractmethod
    async def check_login(self): pass

    @abstractmethod
    async def do_login(self): pass

    @abstractmethod
    async def navigate_to_publish(self): pass

    @abstractmethod
    async def fill_category(self, cat): pass

    @abstractmethod
    async def fill_basic_info(self, product): pass

    @abstractmethod
    async def upload_product_images(self, paths): pass

    @abstractmethod
    async def fill_attributes(self, attrs): pass

    @abstractmethod
    async def fill_sku_info(self, skus): pass

    @abstractmethod
    async def submit_as_draft(self): pass

    @abstractmethod
    async def publish_draft(self, draft_id): pass

    async def screenshot(self, name):
        try:
            path = os.path.join(self._shots_dir, f"{self.platform}_{name}.png")
            await self.page.screenshot(path=path, full_page=True)
            return path
        except Exception as e:
            print(f"[{self.platform}] Screenshot failed: {e}")

    async def safe_click(self, selector, timeout=10000):
        try:
            await self.page.wait_for_selector(selector, state="visible", timeout=timeout)
            await self.page.click(selector)
            return True
        except Exception:
            return False

    async def safe_fill(self, selector, value, timeout=10000):
        try:
            await self.page.wait_for_selector(selector, state="visible", timeout=timeout)
            await self.page.fill(selector, str(value))
            return True
        except Exception:
            return False

    async def upload_file(self, selector, paths):
        try:
            await self.page.locator(selector).set_input_files(paths)
            return True
        except Exception as e:
            print(f"[{self.platform}] Upload failed: {e}")
            return False

    async def wait_for_any(self, selectors, timeout=15000):
        for sel in selectors:
            try:
                await self.page.wait_for_selector(sel, state="visible", timeout=timeout // len(selectors))
                return sel
            except Exception:
                continue

    async def full_pipeline_async(self, product):
        result = {"success": False, "draft_id": None, "error": None, "steps": []}
        try:
            if not await self.init_session():
                result["error"] = "browser session failed"
                return result
            result["steps"].append("session_init")

            if not await self.check_login():
                ok, msg = await self.do_login()
                if not ok:
                    result["error"] = f"login failed: {msg}"
                    await self.release()
                    return result
                await browser_pool.save_state(self.platform, self.shop_id)
            result["steps"].append("login_ok")

            if not await self.navigate_to_publish():
                result["error"] = "navigate to publish page failed"
                await self.release()
                return result
            result["steps"].append("navigate_ok")

            cat = product.get("platform_category", self.shop_cfg.get("category_cid", ""))
            if cat and not await self.fill_category(cat):
                result["error"] = "category selection failed"
                await self.release()
                return result
            result["steps"].append("category_ok")

            if not await self.fill_basic_info(product):
                result["error"] = "basic info fill failed"
                await self.release()
                return result
            result["steps"].append("basic_info_ok")

            images = product.get("main_images", [])
            if images and not await self.upload_product_images(images):
                result["error"] = "image upload failed"
                await self.release()
                return result
            result["steps"].append("images_ok")

            ok, draft_id = await self.submit_as_draft()
            if not ok:
                result["error"] = str(draft_id)
                await self.release()
                return result

            result["success"] = True
            result["draft_id"] = draft_id
            result["steps"].append("draft_created")
            await self.screenshot("draft_success")
        except Exception as e:
            result["error"] = str(e)
            await self.screenshot("error")
        finally:
            await self.release()
        return result


print("[BrowserBase] BrowserPlatformAdapter defined")
