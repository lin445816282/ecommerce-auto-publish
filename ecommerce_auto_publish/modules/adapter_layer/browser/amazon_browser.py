"""亚马逊卖家中心浏览器自动化适配器"""
import asyncio
import time
from typing import Dict, List, Any, Tuple

from .browser_base import BrowserPlatformAdapter, PLATFORM_URLS

SELECTORS = {
    "login_email": '#ap_email, input[type="email"]',
    "login_password": '#ap_password, input[type="password"]',
    "login_submit": '#signInSubmit, [type="submit"]',
    "login_success": '#sc-content, .seller-central-nav',

    "publish_page": '.product-publish, .add-a-product',
    "publish_entry": 'a:has-text("Add a Product"), a:has-text("Inventory")',

    "category_search": 'input[placeholder*="Search"]',
    "category_result": '.category-result-item:first-child, .search-result li',

    "title_input": '#product-title, input[name*="title"]',
    "price_input": '#standard_price, input[name*="price"], input[name*="StandardPrice"]',
    "stock_input": '#quantity, input[name*="quantity"]',
    "desc_frame": 'iframe[title*="description"], #product-description',

    "image_upload": 'input[type="file"][accept*="image"]',
    "image_item": '.image-preview, .upload-success',

    "brand_input": '#brand, input[name*="brand"]',

    "submit_draft": 'button:has-text("Save"), button:has-text("Save as draft")',
    "submit_publish": 'button:has-text("Publish"), button:has-text("Submit")',
    "draft_success": '.success-message, .alert-success',
}


class AmazonBrowserAdapter(BrowserPlatformAdapter):
    """Amazon Seller Central 浏览器自动化"""

    async def check_login(self) -> bool:
        try:
            urls = PLATFORM_URLS["amazon"]
            await self.page.goto(urls["publish"], wait_until="domcontentloaded", timeout=20000)
            await asyncio.sleep(2)
            if "signin" in self.page.url or "ap/signin" in self.page.url:
                return False
            marker = await self.wait_for_any([SELECTORS["login_success"]], timeout=5000)
            return marker is not None
        except Exception as e:
            print(f"[amazon] check_login error: {e}")
            return False

    async def do_login(self) -> Tuple[bool, str]:
        urls = PLATFORM_URLS["amazon"]
        await self.page.goto(urls["login"], wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(2)
        await self.screenshot("amazon_login")

        email = self.shop_cfg.get("email") or self.shop_cfg.get("account", "")
        password = self.shop_cfg.get("password", "")

        if email and password:
            print(f"[amazon] 使用账号密码登录: {email[:8]}...")
            await self.safe_fill(SELECTORS["login_email"], email)
            await self.safe_fill(SELECTORS["login_password"], password)
            await self.safe_click(SELECTORS["login_submit"], timeout=5000)
            await asyncio.sleep(3)

        for _ in range(60):
            await asyncio.sleep(2)
            if "signin" not in self.page.url:
                print("[amazon] 登录成功")
                return True, "登录成功"

        return False, "登录超时(120秒)"

    async def navigate_to_publish(self) -> bool:
        try:
            urls = PLATFORM_URLS["amazon"]
            await self.page.goto(urls["publish"], wait_until="domcontentloaded", timeout=20000)
            await asyncio.sleep(3)
            await self.screenshot("publish")
            return True
        except Exception as e:
            print(f"[amazon] navigate error: {e}")
            return False

    async def fill_category(self, category_path: str) -> bool:
        leaf = category_path.split(">>")[-1].strip()
        await self.safe_fill(SELECTORS["category_search"], leaf)
        await self.page.keyboard.press("Enter")
        await asyncio.sleep(2)
        await self.safe_click(SELECTORS["category_result"], timeout=3000)
        return True

    async def fill_basic_info(self, product: Dict[str, Any]) -> bool:
        title = str(product.get("title", ""))[:200]
        price = product.get("price", 0)
        stock = product.get("stock", 100)

        if title:
            await self.safe_fill(SELECTORS["title_input"], title)
        if int(price) > 0:
            await self.safe_fill(SELECTORS["price_input"], f"{float(price):.2f}")
        await self.safe_fill(SELECTORS["stock_input"], str(int(stock)))
        await self.screenshot("info_filled")
        return True

    async def upload_product_images(self, image_paths: List[str]) -> bool:
        if not image_paths:
            return True
        valid = image_paths[:7]
        fi = self.page.locator(SELECTORS["image_upload"])
        if await fi.count() > 0:
            await fi.first.set_input_files(valid)
            await asyncio.sleep(3)
        return True

    async def fill_attributes(self, attrs: Dict[str, Any]) -> bool:
        brand = attrs.get("brand") or attrs.get("Brand") or ""
        if brand:
            await self.safe_fill(SELECTORS["brand_input"], brand)
        return True

    async def fill_sku_info(self, skus: List[Dict]) -> bool:
        return True

    async def submit_as_draft(self) -> Tuple[bool, str]:
        await self.safe_click(SELECTORS["submit_draft"], timeout=10000)
        await asyncio.sleep(3)
        await self.screenshot("draft_saved")
        return True, f"amz_draft_{int(time.time())}"

    async def publish_draft(self, draft_id: str) -> Tuple[bool, str]:
        await self.safe_click(SELECTORS["submit_publish"], timeout=10000)
        return True, "上架成功"


print("[AmazonBrowserAdapter] loaded")
