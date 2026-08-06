"""产品源 — 1688商品信息抓取"""
import re
import json
from typing import Dict, Optional, List
from urllib.parse import urlparse

import httpx


class AlibabaCrawler:
    """1688商品抓取器"""

    BASE_URL = "https://detail.1688.com"

    def __init__(self, timeout: int = 30):
        self.client = httpx.Client(timeout=timeout, follow_redirects=True)
        self.client.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        })

    def parse_url(self, url: str) -> Optional[str]:
        """从1688链接提取商品ID"""
        # 支持格式:
        # https://detail.1688.com/offer/123456789.html
        # https://detail.1688.com/offer/123456789.html?spm=...
        patterns = [
            r'/offer/(\d+)\.html',
            r'offerId=(\d+)',
        ]
        for pat in patterns:
            m = re.search(pat, url)
            if m:
                return m.group(1)
        return None

    def crawl(self, url: str) -> Dict:
        """
        抓取商品信息
        返回: {"success": bool, "data": dict, "error": str}
        """
        offer_id = self.parse_url(url)
        if not offer_id:
            return {"success": False, "error": "无法解析1688商品ID", "data": None}

        # MVP阶段：模拟数据（实际接入需要处理反爬）
        # TODO: 接入真实爬虫或1688开放平台API
        try:
            # 模拟API响应
            product_data = self._mock_crawl(offer_id)
            return {"success": True, "data": product_data, "error": None}
        except Exception as e:
            return {"success": False, "error": str(e), "data": None}

    def _mock_crawl(self, offer_id: str) -> Dict:
        """模拟抓取数据（MVP阶段）"""
        return {
            "source_id": offer_id,
            "title": f"1688商品-{offer_id}",
            "desc": "高品质产品，厂家直供，批发优惠。材质优良，工艺精湛，支持定制。",
            "price": 39.9,
            "wholesale_price": 29.9,
            "min_order": 10,
            "stock": 9999,
            "category": "日用百货",
            "main_images": [
                f"https://cbu01.alicdn.com/img/{offer_id}/main1.jpg",
                f"https://cbu01.alicdn.com/img/{offer_id}/main2.jpg",
            ],
            "detail_images": [
                f"https://cbu01.alicdn.com/img/{offer_id}/detail1.jpg",
            ],
            "spec_json": {
                "颜色": ["白色", "黑色", "蓝色"],
                "尺寸": ["S", "M", "L", "XL"],
            },
            "attrs_json": {
                "材质": "纯棉",
                "适用场景": "日常休闲",
                "产地": "浙江义乌",
            },
            "shipping": {
                "weight": 0.5,
                "unit": "kg",
            }
        }


class ProductImporter:
    """产品导入器：从不同来源导入，自动去重"""

    def __init__(self):
        self.crawler = AlibabaCrawler()

    def import_from_1688(self, url: str) -> Dict:
        """从1688链接导入"""
        result = self.crawler.crawl(url)
        if not result["success"]:
            return result

        data = result["data"]
        # 生成内部SKU
        data["inner_sku"] = f"1688-{data['source_id']}"
        data["source_type"] = "1688"
        data["source_url"] = url
        return {"success": True, "data": data}

    def import_manual(self, form_data: Dict) -> Dict:
        """手动录入"""
        required = ["title", "price"]
        missing = [f for f in required if not form_data.get(f)]
        if missing:
            return {"success": False, "error": f"缺少必填字段: {missing}"}

        data = {
            "inner_sku": form_data.get("sku", f"MAN-{int(__import__('time').time())}"),
            "title": form_data["title"],
            "desc": form_data.get("desc", ""),
            "price": float(form_data["price"]),
            "cost_price": float(form_data.get("cost_price", 0)),
            "stock": int(form_data.get("stock", 0)),
            "main_images": form_data.get("images", []),
            "source_type": "manual",
            "source_url": "",
            "attrs_json": form_data.get("attrs", {}),
            "spec_json": form_data.get("specs", {}),
        }
        return {"success": True, "data": data}


product_importer = ProductImporter()
print("[ProductSource] AlibabaCrawler + ProductImporter ready.")
