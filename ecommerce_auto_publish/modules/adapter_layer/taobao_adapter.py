"""淘宝/天猫平台适配器"""
from .base_adapter import BasePlatformAdapter
from typing import Dict, Any, List, Optional


class TaobaoAdapter(BasePlatformAdapter):
    """淘宝适配器：处理属性下拉勾选、登录态保持、图片上传"""

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
        """翻译为主表字段 -> 淘宝API字段"""
        return {
            "title": data.get("title", ""),
            "desc": data.get("desc", ""),
            "price": str(int(float(data.get("price", 0)) * 100)),  # 淘宝价格单位: 分
            "num": data.get("stock", 0),
            "pic_urls": data.get("images", []),
            "detail_images": data.get("detail_images", []),
            "category_cid": self.shop_cfg.get("category_cid", ""),
        }

    def check_required(self, payload: Dict[str, Any]) -> List[str]:
        required = ["title", "price", "pic_urls", "category_cid"]
        return [f for f in required if not payload.get(f)]

    def upload_images(self, image_list: List[str]) -> List[str]:
        """上传图片到淘宝图片空间"""
        # TODO: 调用淘宝 API taobao.picture.upload
        # MVP阶段返回原路径
        return image_list

    def submit_draft(self, payload: Dict[str, Any]) -> Optional[str]:
        """调用淘宝 taobao.item.add 提交草稿"""
        # TODO: 实际调用淘宝API
        # 模拟返回草稿ID
        import time
        return f"tb_draft_{int(time.time())}"

    def publish_draft(self, draft_id: str) -> bool:
        """草稿正式上架"""
        # TODO: 调用淘宝API上架
        return True

