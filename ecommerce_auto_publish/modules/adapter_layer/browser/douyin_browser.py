"""抖音/抖店浏览器自动化适配器"""
import asyncio
import time
from typing import Dict, List, Any, Tuple

from .browser_base import BrowserPlatformAdapter, PLATFORM_URLS

SELECTORS = {
    "login_phone": 'input[placeholder*="手机"], input[type="tel"]',
    "login_code": 'input[placeholder*="验证码"], input[placeholder*="短信"]',
    "login_get_code": 'button:has-text("获取验证码"), .get-code-btn',
    "login_submit": 'button:has-text("登录"), .login-btn',
    "login_success": '.nav-menu, .sidebar, .shop-header',

    "publish_page": '.product-publish, .goods-publish, .publish-container',
    "publish_entry": 'a:has-text("发布商品"), span:has-text("发布")',

    "category_select": '.category-select, [class*="category"] input',
    "category_result": '.category-item:first-child',

    "title_input": 'input[placeholder*="标题"]',
    "price_input": 'input[placeholder*="售价"], input[placeholder*="价格"]',
    "stock_input": 'input[placeholder*="库存"]',
    "desc_frame": 'iframe[title*="详情"], [class*="desc"] iframe',

    "image_upload": 'input[type="file"][accept*="image"]',
    "image_item": '.image-item, [class*="upload"][class*="success"]',

    "brand_input": 'input[placeholder*="品牌"]',

    "submit_draft": 'button:has-text("保存草稿"), button:has-text("草稿"), .draft-btn',
    "submit_publish": 'button:has-text("上架"), button:has-text("发布")',
    "draft_success": '[class*="success"], .toast',
}


class DouyinBrowserAdapter(BrowserPlatformAdapter):
    """抖店商家后台浏览器自动化"""

    async def check_login(self) -> bool:
        try:
            urls = PLATFORM_URLS["douyin"]
            await self.page.goto(urls["publish"], wait_until="domcontentloaded", timeout=15000)
            await asyncio.sleep(2)
            if "login" in self.page.url:
                return False
            marker = await self.wait_for_any([SELECTORS["login_success"]], timeout=5000)
            return marker is not None
        except Exception as e:
            print(f"[douyin] check_login error: {e}")
            return False

    async def do_login(self) -> Tuple[bool, str]:
        """抖店登录 — 短信验证码"""
        urls = PLATFORM_URLS["douyin"]
        await self.page.goto(urls["login"], wait_until="domcontentloaded", timeout=15000)
        await asyncio.sleep(2)
        await self.screenshot("douyin_login")

        phone = self.shop_cfg.get("phone", "")
        if phone:
            await self.safe_fill(SELECTORS["login_phone"], phone)
            await self.safe_click(SELECTORS["login_get_code"], timeout=3000)
            print("[douyin] 验证码已发送，请在120秒内输入")
            await self.screenshot("douyin_wait_code")

        for _ in range(60):
            await asyncio.sleep(2)
            if "login" not in self.page.url:
                print("[douyin] 登录成功")
                return True, "登录成功"

        return False, "登录超时(120秒)"

    async def navigate_to_publish(self) -> bool:
        try:
            urls = PLATFORM_URLS["douyin"]
            await self.page.goto(urls["publish"], wait_until="domcontentloaded", timeout=15000)
            await asyncio.sleep(3)
            await self.screenshot("publish")
            return True
        except Exception as e:
            print(f"[douyin] navigate error: {e}")
            return False

    async def fill_category(self, category_path: str) -> bool:
        leaf = category_path.split(">>")[-1].strip()
        await self.safe_fill(SELECTORS["category_select"], leaf)
        await self.page.keyboard.press("Enter")
        await asyncio.sleep(2)
        await self.safe_click(SELECTORS["category_result"], timeout=3000)
        return True

    async def fill_basic_info(self, product: Dict[str, Any]) -> bool:
        title = str(product.get("title", ""))[:60]
        price = product.get("price", 0)
        stock = product.get("stock", 100)

        if title:
            await self.safe_fill(SELECTORS["title_input"], title)
        if int(price) > 0:
            await self.safe_fill(SELECTORS["price_input"], str(int(float(price))))
        await self.safe_fill(SELECTORS["stock_input"], str(int(stock)))
        await self.screenshot("info_filled")
        return True

    async def upload_product_images(self, image_paths: List[str]) -> bool:
        if not image_paths:
            return True
        valid = image_paths[:5]
        fi = self.page.locator(SELECTORS["image_upload"])
        if await fi.count() > 0:
            await fi.first.set_input_files(valid)
            await asyncio.sleep(3)
        return True

    async def fill_attributes(self, attrs: Dict[str, Any]) -> bool:
        return True

    async def fill_sku_info(self, skus: List[Dict]) -> bool:
        return True

    async def submit_as_draft(self) -> Tuple[bool, str]:
        await self.safe_click(SELECTORS["submit_draft"], timeout=10000)
        await asyncio.sleep(3)
        await self.screenshot("draft_saved")
        return True, f"dy_draft_{int(time.time())}"

    async def publish_draft(self, draft_id: str) -> Tuple[bool, str]:
        await self.safe_click(SELECTORS["submit_publish"], timeout=10000)
        return True, "上架成功"


print("[DouyinBrowserAdapter] loaded")
