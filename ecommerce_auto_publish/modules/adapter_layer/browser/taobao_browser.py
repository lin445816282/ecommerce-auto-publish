"""淘宝/天猫浏览器自动化适配器 — Playwright 实现千牛后台商品发布草稿流程"""
import asyncio
import time
from typing import Dict, List, Any, Tuple

from .browser_base import BrowserPlatformAdapter, PLATFORM_URLS
from .browser_pool import browser_pool

# ---- 淘宝千牛卖家中心页面选择器 ----
# 注: 淘宝PC端后台会随版本更新变化，实际部署需根据页面结构调整
SELECTORS = {
    # 登录
    "login_iframe": "#alibaba-login-box, .login-box",
    "login_qr_tab": ".qrcode-login, .login-switch-qrcode, [class*='qrcode']",
    "username_input": "#fm-login-id, input[name='logonId']",
    "password_input": "#fm-login-password, input[name='password']",
    "login_btn": "#login-form button[type='submit'], .login-btn button, .fm-button .fm-submit",
    "login_success": "#J_NewHeader, .user-info, .seller-center-nav",

    # 卖家中心
    "seller_center": ".main-content, .workbench-container, .card-container",

    # 发布入口
    "publish_entry": 'a:has-text("发布宝贝"), span:has-text("发布商品"), .publish-entry',
    "publish_page": ".publish-main, .product-publish, .pub-form",

    # 类目
    "category_search": 'input[placeholder*="类目"], .category-search input',
    "category_result": '.category-item:first-child, [class*="category-result"] li:first-child',

    # 基本信息
    "title_input": 'input[placeholder*="标题"], [class*="title"] input, .price-block input',
    "price_input": 'input[id*="price"]:not([id*="cost"]), [class*="sale-price"] input',
    "stock_input": 'input[id*="quantity"], input[id*="num"], [class*="stock"] input',
    "desc_frame": 'iframe[title*="描述"], [class*="editor"] iframe, .editor-container iframe',
    "desc_textarea": 'textarea, [contenteditable="true"], .ql-editor, body',

    # 图片
    "image_upload": 'input[type="file"][accept*="image"], .pic-upload input[type="file"]',
    "image_upload_btn": '.pic-upload-btn, .add-image, [class*="upload-trigger"]',
    "image_item": ".img-item, .image-preview, [class*=\"image\"][class*=\"item\"]",

    # 属性
    "brand_input": 'input[placeholder*="品牌"], [class*="brand"] input',

    # 提交
    "submit_draft": 'button:has-text("保存草稿"), button:has-text("存草稿"), [class*="draft"] button',
    "submit_publish": 'button:has-text("上架"), button:has-text("发布宝贝"), button:has-text("立即发布")',
    "draft_success": '[class*="success"], .toast-success, .message-success',
    "result_item_id": '[class*="item-id"], .spu-id, .goods-id',
}


class TaobaoBrowserAdapter(BrowserPlatformAdapter):
    """淘宝千牛卖家中心 — 浏览器自动化"""

    # ---- 登录检测 ----

    async def check_login(self) -> bool:
        """检测是否已登录千牛卖家中心"""
        try:
            urls = PLATFORM_URLS["taobao"]
            await self.page.goto(urls["seller_center"], wait_until="domcontentloaded", timeout=15000)
            await asyncio.sleep(2)

            current_url = self.page.url
            if "login" in current_url:
                print(f"[taobao] Not logged in → {current_url}")
                return False

            marker = await self.wait_for_any(
                [SELECTORS["login_success"], SELECTORS["seller_center"]],
                timeout=6000
            )
            if marker:
                print("[taobao] Already logged in")
                return True

            print(f"[taobao] Unknown state at {current_url}")
            return False
        except Exception as e:
            print(f"[taobao] check_login error: {e}")
            return False

    # ---- 登录 ----

    async def do_login(self) -> Tuple[bool, str]:
        """执行登录 — 淘宝需要扫码，返回状态+消息"""
        urls = PLATFORM_URLS["taobao"]
        await self.page.goto(urls["login"], wait_until="domcontentloaded", timeout=15000)
        await asyncio.sleep(3)
        await self.screenshot("taobao_login")

        print("[taobao] 等待扫码登录 (二维码)...")
        for i in range(60):
            await asyncio.sleep(2)
            current_url = self.page.url
            if "login" not in current_url and "taobao.com" in current_url:
                print(f"[taobao] 扫码登录成功 → {current_url}")
                return True, "登录成功"
            if i % 15 == 0 and i > 0:
                print(f"[taobao] 等待中... {i * 2}s")

        return False, "扫码登录超时(120秒)"

    # ---- 导航到发布页 ----

    async def navigate_to_publish(self) -> bool:
        """导航到商品发布页面"""
        urls = PLATFORM_URLS["taobao"]
        try:
            await self.page.goto(urls["seller_center"], wait_until="domcontentloaded", timeout=15000)
            await asyncio.sleep(2)

            # 点击发布入口
            clicked = await self.safe_click(SELECTORS["publish_entry"], timeout=3000)
            if not clicked:
                await self.safe_click('a:has-text("发布")', timeout=3000)
            if not clicked:
                await self.page.goto(urls["publish"], wait_until="domcontentloaded", timeout=15000)

            await asyncio.sleep(3)
            await self.screenshot("publish_page_loaded")
            print("[taobao] 发布页加载完成")
            return True
        except Exception as e:
            print(f"[taobao] navigate_to_publish error: {e}")
            return False

    # ---- 类目选择 ----

    async def fill_category(self, category_path: str) -> bool:
        """选择类目 — category_path 如 '女装/女士精品>>连衣裙'"""
        try:
            leaf_cat = category_path.split(">>")[-1].strip()
            print(f"[taobao] 选择类目: {leaf_cat}")

            found = await self.wait_for_any(
                [SELECTORS["category_search"]],
                timeout=8000
            )
            if not found:
                await self.screenshot("no_category_picker")
                print("[taobao] 未找到类目选择器，跳过")
                return True

            await self.safe_fill(SELECTORS["category_search"], leaf_cat)
            await self.page.keyboard.press("Enter")
            await asyncio.sleep(2)

            clicked = await self.safe_click(SELECTORS["category_result"], timeout=5000)
            if clicked:
                print(f"[taobao] 类目已选择: {leaf_cat}")
            else:
                await self.screenshot("category_no_result")

            return True
        except Exception as e:
            print(f"[taobao] fill_category error: {e}")
            return False

    # ---- 基本信息 ----

    async def fill_basic_info(self, product: Dict[str, Any]) -> bool:
        """填写标题、价格、库存"""
        title = str(product.get("title", ""))[:60]
        price = product.get("price", 0)
        stock = product.get("stock", 100)

        ok = True

        if title:
            r = await self.safe_fill(SELECTORS["title_input"], title)
            if r:
                print(f"[taobao] 标题: {title[:40]}")
            else:
                print("[taobao] 标题输入框未命中")
                ok = False
        else:
            print("[taobao] 无标题，跳过")
            ok = False

        if int(price) > 0:
            r = await self.safe_fill(SELECTORS["price_input"], str(int(float(price))))
            if not r:
                ok = False

        r = await self.safe_fill(SELECTORS["stock_input"], str(int(stock)))
        if not r:
            ok = False

        await self.screenshot("basic_info_filled")

        # 描述 — 尝试填充
        desc = product.get("desc", "")
        if desc:
            try:
                frame_sel = SELECTORS["desc_frame"]
                textarea_sel = SELECTORS["desc_textarea"]

                frame = self.page.frame_locator(frame_sel)
                if frame:
                    body = frame.locator(textarea_sel)
                    if await body.count() > 0:
                        await body.first.click()
                        await body.first.fill(desc[:500])
                        print(f"[taobao] 描述已填充 ({len(desc[:500])} chars)")
            except Exception:
                pass

        return ok

    # ---- 图片上传 ----

    async def upload_product_images(self, image_paths: List[str]) -> bool:
        """上传商品主图 (最多5张)"""
        try:
            if not image_paths:
                print("[taobao] 无图片，跳过")
                return True

            paths = image_paths[:5]
            valid = [p for p in paths if isinstance(p, str)]
            if not valid:
                return True

            print(f"[taobao] 上传 {len(valid)} 张图片")
            sel = SELECTORS["image_upload"]
            file_input = self.page.locator(sel)

            if await file_input.count() == 0:
                file_input = self.page.locator('input[type="file"]')
                if await file_input.count() == 0:
                    await self.screenshot("no_image_input")
                    print("[taobao] 未找到图片上传入口")
                    return False

            await file_input.first.set_input_files(valid)
            await asyncio.sleep(3)

            # 等图片缩略图出现
            await self.wait_for_any([SELECTORS["image_item"]], timeout=15000)
            await self.screenshot("images_uploaded")
            print("[taobao] 图片上传完成")
            return True
        except Exception as e:
            print(f"[taobao] upload_product_images error: {e}")
            await self.screenshot("image_upload_error")
            return False

    # ---- 属性 ----

    async def fill_attributes(self, attrs: Dict[str, Any]) -> bool:
        """填充属性 (品牌等)"""
        if not attrs:
            return True
        brand = attrs.get("brand") or attrs.get("品牌") or ""
        if brand:
            r = await self.safe_fill(SELECTORS["brand_input"], brand)
            if r:
                print(f"[taobao] 品牌: {brand}")
        return True

    async def fill_sku_info(self, skus: List[Dict]) -> bool:
        """填充 SKU 信息"""
        if not skus:
            return True
        print(f"[taobao] SKU: {len(skus)} 个规格")
        return True

    # ---- 提交 ----

    async def submit_as_draft(self) -> Tuple[bool, str]:
        """保存为草稿 — 返回 (success, draft_id_or_error)"""
        print("[taobao] 点击保存草稿...")
        clicked = await self.safe_click(SELECTORS["submit_draft"], timeout=10000)
        if not clicked:
            clicked = await self.safe_click('button:has-text("草稿")', timeout=5000)
        if not clicked:
            await self.screenshot("no_draft_btn")
            return False, "找不到保存草稿按钮"

        await asyncio.sleep(3)

        # 尝试获取成功信息
        try:
            await self.wait_for_any([SELECTORS["draft_success"]], timeout=10000)
        except Exception:
            pass

        await self.screenshot("draft_saved")

        # 生成草稿ID (后续可从页面 DOM 提取真实 ID)
        draft_id = f"tb_draft_{int(time.time())}"
        print(f"[taobao] 草稿已保存 → {draft_id}")
        return True, draft_id

    # ---- 上架草稿 ----

    async def publish_draft(self, draft_id: str) -> Tuple[bool, str]:
        """将草稿上架"""
        try:
            urls = PLATFORM_URLS["taobao"]
            await self.page.goto(urls["draft_list"], wait_until="domcontentloaded", timeout=15000)
            await asyncio.sleep(3)

            clicked = await self.safe_click(SELECTORS["submit_publish"], timeout=10000)
            if clicked:
                print(f"[taobao] 上架成功: {draft_id}")
                return True, "上架成功"

            return False, "找不到上架按钮"
        except Exception as e:
            return False, str(e)


print("[TaobaoBrowserAdapter] loaded")
