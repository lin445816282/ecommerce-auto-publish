"""抖店平台适配器"""
from .base_adapter import BasePlatformAdapter
from typing import Dict, Any, List, Optional


class DouyinAdapter(BasePlatformAdapter):
    """抖店适配器"""

    def read_master_product(self, master_data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "sku": master_data.get("inner_sku", ""),
            "title": master_data.get("title", ""),
            "desc": master_data.get("desc", ""),
            "price": master_data.get("price", 0),
            "stock": master_data.get("stock", 0),
            "images": master_data.get("main_images", []),
            "detail_images": master_data.get("detail_images", []),
            "brand": master_data.get("attrs_json", {}).get("品牌", "其他"),
        }

    def translate_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "product_name": data.get("title", ""),
            "description": data.get("desc", ""),
            "price": int(float(data.get("price", 0)) * 100),
            "stock_num": data.get("stock", 0),
            "pic_urls": data.get("images", []),
            "detail_urls": data.get("detail_images", []),
            "brand_name": data.get("brand", "其他"),
            "pay_type": 1,
            "delivery_method": 1,
            "category_leaf_id": self.shop_cfg.get("category_id", ""),
        }

    def check_required(self, payload: Dict[str, Any]) -> List[str]:
        required = ["product_name", "price", "pic_urls", "category_leaf_id"]
        missing = []
        for f in required:
            val = payload.get(f)
            if val is None or (isinstance(val, str) and val == ""):
                missing.append(f)
        return missing

    def upload_images(self, image_list: List[str]) -> List[str]:
        return image_list

    def submit_draft(self, payload: Dict[str, Any]) -> Optional[str]:
        import time
        return f"dy_draft_{int(time.time())}"

    def publish_draft(self, draft_id: str) -> bool:
        return True
