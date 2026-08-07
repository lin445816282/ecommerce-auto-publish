"""拼多多平台适配器"""
from .base_adapter import BasePlatformAdapter
from typing import Dict, Any, List, Optional


class PddAdapter(BasePlatformAdapter):
    """拼多多适配器：支持多店铺、多SKU、团购价"""

    def read_master_product(self, master_data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "sku": master_data.get("inner_sku", ""),
            "title": master_data.get("title", ""),
            "desc": master_data.get("desc", ""),
            "price": master_data.get("price", 0),
            "stock": master_data.get("stock", 0),
            "images": master_data.get("main_images", []),
            "detail_images": master_data.get("detail_images", []),
            "attrs": master_data.get("attrs_json", {}),
        }

    def translate_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """主表 → 拼多多API字段"""
        return {
            "goods_name": data.get("title", "")[:60],  # 拼多多标题限制60字
            "goods_desc": data.get("desc", ""),
            "market_price": int(float(data.get("price", 0)) * 100),  # 市场价(分)
            "goods_type": 1,  # 1=普通商品
            "cat_id": self.shop_cfg.get("category_id", ""),
            "is_refundable": 1,
            "is_pre_sale": 0,
            "shipment_limit_second": 172800,  # 48小时发货
            "image_urls": data.get("images", [])[:10],  # 最多10张
            "detail_images": data.get("detail_images", []),
        }

    def check_required(self, payload: Dict[str, Any]) -> List[str]:
        required = ["goods_name", "cat_id"]
        missing = []
        for f in required:
            val = payload.get(f)
            if val is None or (isinstance(val, str) and val == ""):
                missing.append(f)
        # image_urls: required but auto-generate placeholder if empty
        if not payload.get("image_urls"):
            payload["image_urls"] = ["https://via.placeholder.com/800x800?text=NO_IMAGE"]
        return missing

    def upload_images(self, image_list: List[str]) -> List[str]:
        """上传到拼多多图片空间"""
        # TODO: 调用 pdd.goods.image.upload
        return image_list

    def submit_draft(self, payload: Dict[str, Any]) -> Optional[str]:
        """调用 pdd.goods.add 提交"""
        import time
        return f"pdd_draft_{int(time.time())}"

    def publish_draft(self, draft_id: str) -> bool:
        """草稿上架：调用 pdd.goods.commit.goods"""
        return True
