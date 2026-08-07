"""淘宝/天猫平台适配器"""
from .base_adapter import BasePlatformAdapter
from typing import Dict, Any, List, Optional


class TaobaoAdapter(BasePlatformAdapter):
    """淘宝适配器"""

    def read_master_product(self, master_data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "sku": master_data.get("inner_sku", ""),
            "title": master_data.get("title", ""),
            "desc": master_data.get("desc", ""),
            "price": master_data.get("price", 0),
            "stock": master_data.get("stock", 0),
            "images": master_data.get("main_images", []),
            "detail_images": master_data.get("detail_images", []),
        }

    def translate_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "title": data.get("title", ""),
            "desc": data.get("desc", ""),
            "price": str(int(float(data.get("price", 0)) * 100)),
            "num": data.get("stock", 0),
            "pic_urls": data.get("images", []),
            "detail_images": data.get("detail_images", []),
            "category_cid": self.shop_cfg.get("category_cid", ""),
            "type": "fixed",
        }

    def check_required(self, payload: Dict[str, Any]) -> List[str]:
        required = ["title", "price", "category_cid"]
        missing = []
        for f in required:
            val = payload.get(f)
            if val is None or (isinstance(val, str) and val == ""):
                missing.append(f)
        # pic_urls: required but auto-fill placeholder if empty
        if not payload.get("pic_urls"):
            payload["pic_urls"] = ["https://via.placeholder.com/800x800?text=NO_IMAGE"]
        return missing

    def upload_images(self, image_list: List[str]) -> List[str]:
        return image_list

    def submit_draft(self, payload: Dict[str, Any]) -> Optional[str]:
        import time
        return f"tb_draft_{int(time.time())}"

    def publish_draft(self, draft_id: str) -> bool:
        return True
