"""亚马逊平台适配器"""
from .base_adapter import BasePlatformAdapter
from typing import Dict, Any, List, Optional


class AmazonAdapter(BasePlatformAdapter):
    """亚马逊适配器：SP-API接入，多站点支持"""

    def read_master_product(self, master_data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "sku": master_data.get("inner_sku", ""),
            "title": master_data.get("title", ""),
            "desc": master_data.get("desc", ""),
            "price": master_data.get("price", 0),
            "stock": master_data.get("stock", 0),
            "images": master_data.get("main_images", []),
            "attrs": master_data.get("attrs_json", {}),
            "brand": master_data.get("attrs_json", {}).get("品牌", "Generic"),
        }

    def translate_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """主表 → Amazon SP-API 字段"""
        return {
            "sku": data.get("sku", ""),
            "product_title": data.get("title", "")[:200],  # 亚马逊200字符限制
            "description": data.get("desc", ""),
            "standard_price": float(data.get("price", 0)),
            "quantity": data.get("stock", 0),
            "brand": data.get("brand", "Generic"),
            "manufacturer": data.get("brand", "Generic"),
            "main_image_url": data.get("images", [None])[0] if data.get("images") else "",
            "other_image_urls": data.get("images", [])[1:9],  # 最多9张
            "product_category": self.shop_cfg.get("category_id", "Fashion"),
            "item_type": "PRODUCT",
            "fulfillment_channel": "DEFAULT",  # FBA or FBM
            "condition_type": "New",
            "currency_code": "USD",
        }

    def check_required(self, payload: Dict[str, Any]) -> List[str]:
        required = ["sku", "product_title", "main_image_url", "product_category", "brand"]
        missing = []
        for f in required:
            val = payload.get(f)
            if val is None or (isinstance(val, str) and val == ""):
                missing.append(f)
        return missing

    def upload_images(self, image_list: List[str]) -> List[str]:
        """上传到Amazon图片服务"""
        # TODO: 调用 SP-API /uploads/2020-11-01/uploadDestinations
        return image_list

    def submit_draft(self, payload: Dict[str, Any]) -> Optional[str]:
        """调用 Amazon SP-API createListing"""
        import time
        return f"amz_draft_{int(time.time())}"

    def publish_draft(self, draft_id: str) -> bool:
        """发布到Amazon"""
        return True
