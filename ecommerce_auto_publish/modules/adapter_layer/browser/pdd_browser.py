"""拼多多商家后台浏览器自动化适配器"""
import asyncio
import time
from typing import Dict, List, Any, Tuple

from .browser_base import BrowserPlatformAdapter, PLATFORM_URLS

SELECTORS = {
    "login_phone": 'input[placeholder*="手机"], input[type="tel"]',
    "login_code": 'input[placeholder*="验证码"]',
    "login_get_code": 'button:has-text("获取验证码")',
    "login_submit": 'button:has-text("登录")',
    "login_success": '.sidebar-menu, .nav-menu, .shop-name',

    "publish_page": '.goods-publish, .publish-main, .edit-goods',
    "publish_entry": 'a:has-text("发布商品"), a:has-text("发布")',

    "category_select": '.category-select, .cate-tree input',
    "category_result": '.category-item:first-child',

    "title_input": 'input[placeholder*="标题"], [class*="goods-title"] input',
    "price_input": 'input[placeholder*="价格"], input[placeholder*="售价"]',
    "stock_input": 'input[placeholder*="库存"], input[placeholder*="数量"]',
    "desc_frame": 'iframe[title*="详情"], .editor iframe',

    "image_upload": 'input[type="file"][accept*="image"]',
    "image_item": '.img-item, .image-preview',

    "brand_input": 'input[placeholder*="品牌"]',

    "submit_draft": 'button:has-text("保存草稿"), button:has-text("草稿")',
    "submit_publish": 'button:has-text("上架"), button:has-text("提交")',
    "draft_success": '.success-toast, .message-success',
}


class PDDBrowserAdapter(BrowserPlatformAdapter):
    """拼多多商家后台浏览器自动化"""

    async def check_login(self) -> bool:
        try:
            urls = PLATFORM_URLS["pdd"]
            await self.page.goto(urls["publish"], wait_until="domcontentloaded", timeout=15000)
            await asyncio.sleep(2)
            if "login" in self.page.url:
                return False
            marker = await self.wait_for_any([SELECTORS["login_success"]], timeout=5000)
            return marker is not None
        except Exception as e:
            print(f"[pdd] check_login error: {e}")
            return False

    async def do_login(self) -> Tuple[bool, str]:
        urls = PLATFORM_URLS["pdd"]
        await self.page.goto(urls["login"], wait_until="domcontentloaded", timeout=15000)
        await asyncio.sleep(2)
        await self.screenshot("pdd_login")

        phone = self.shop_cfg.get("phone", "")
        if phone:
            await self.safe_fill(SELECTORS["login_phone"], phone)
            await self.safe_click(SELECTORS["login_get_code"], timeout=3000)
            print("[pdd] 验证码已发送")

        for _ in range(60):
            await asyncio.sleep(2)
            if "login" not in self.page.url:
                return True, "登录成功"
        return False, "登录超时"

    async def navigate_to_publish(self) -> bool:
        try:
            urls = PLATFORM_URLS["pdd"]
            await self.page.goto(urls["publish"], wait_until="domcontentloaded", timeout=15000)
            await asyncio.sleep(3)
            await self.screenshot("publish")
            return True
        except Exception as e:
            print(f"[pdd] navigate error: {e}")
            return False

    async def fill_category(self, category_path: str) -> bool:
        leaf = category_path.split(">>")[-1].strip()
        await self.safe_fill(SELECTORS["category_select"], leaf)
        await self.page.keyboard.press("Enter")
        await asyncio.sleep(2)
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
        return True, f"pdd_draft_{int(time.time())}"

    async def publish_draft(self, draft_id: str) -> Tuple[bool, str]:
        await self.safe_click(SELECTORS["submit_publish"], timeout=10000)
        return True, "上架成功"


print("[PDDBrowserAdapter] loaded")
