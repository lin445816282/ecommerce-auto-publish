"""平台适配器基类 — 定义统一接口，各平台继承实现"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional


class BasePlatformAdapter(ABC):
    """适配器基类：共用动作序列，平台值分开"""

    def __init__(self, shop_config: Dict[str, Any]):
        self.shop_cfg = shop_config  # 店铺授权、类目映射配置
        self.platform_name = self.__class__.__name__.replace("Adapter", "").lower()

    @abstractmethod
    def read_master_product(self, master_data: Dict[str, Any]) -> Dict[str, Any]:
        """读取商品主表数据，返回标准化结构"""
        pass

    @abstractmethod
    def translate_fields(self, master_data: Dict[str, Any]) -> Dict[str, Any]:
        """字段翻译：主表字段 -> 平台请求字段"""
        pass

    @abstractmethod
    def check_required(self, platform_payload: Dict[str, Any]) -> List[str]:
        """校验平台必填项，返回缺失字段列表"""
        pass

    @abstractmethod
    def upload_images(self, image_list: List[str]) -> List[str]:
        """上传图片到平台素材库，返回平台图片ID数组"""
        pass

    @abstractmethod
    def submit_draft(self, payload: Dict[str, Any]) -> Optional[str]:
        """提交生成草稿，返回平台草稿ID"""
        pass

    @abstractmethod
    def publish_draft(self, draft_id: str) -> bool:
        """草稿正式上架，返回成功/失败"""
        pass

    def full_pipeline(self, master_data: Dict[str, Any]) -> Dict[str, Any]:
        """完整适配流水线"""
        result = {"success": False, "draft_id": None, "error": None}

        # Step 1: 读取主表
        data = self.read_master_product(master_data)
        print(f"[{self.platform_name}] Step1: read master OK")

        # Step 2: 字段翻译
        payload = self.translate_fields(data)
        print(f"[{self.platform_name}] Step2: translate fields OK")

        # Step 3: 必填校验
        missing = self.check_required(payload)
        if missing:
            result["error"] = f"缺少必填字段: {missing}"
            return result
        print(f"[{self.platform_name}] Step3: required check passed")

        # Step 4: 上传图片
        img_ids = self.upload_images(payload.get("images", []))
        payload["image_ids"] = img_ids
        print(f"[{self.platform_name}] Step4: images uploaded ({len(img_ids)})")

        # Step 5: 提交草稿
        draft_id = self.submit_draft(payload)
        if draft_id:
            result["success"] = True
            result["draft_id"] = draft_id
        else:
            result["error"] = "提交草稿失败"
        return result

