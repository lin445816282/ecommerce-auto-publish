"""商品主表管理 — 增删改查 + 版本管理 + 状态流转"""
import copy
import json
from typing import Dict, List, Optional
from datetime import datetime


class ProductMasterManager:
    """商品主表管理器"""

    STATUS_MAP = {
        0: "草稿",
        1: "待审核",
        2: "已生成平台草稿",
        3: "部分上架",
        4: "全部上架",
        5: "作废",
    }

    def __init__(self):
        self._version_store = {}  # master_id -> list of historical versions

    def validate(self, data: Dict) -> List[str]:
        """校验商品数据完整性"""
        errors = []
        if not data.get("title"):
            errors.append("标题不能为空")
        if not data.get("inner_sku"):
            errors.append("SKU不能为空")
        price = data.get("price", 0)
        if price <= 0:
            errors.append("价格必须大于0")
        return errors

    def save_version(self, master_id: int, data: Dict):
        """保存历史版本"""
        if master_id not in self._version_store:
            self._version_store[master_id] = []
        snapshot = copy.deepcopy(data)
        snapshot["saved_at"] = datetime.utcnow().isoformat()
        snapshot["version"] = len(self._version_store[master_id]) + 1
        self._version_store[master_id].append(snapshot)

    def get_versions(self, master_id: int) -> List[Dict]:
        """获取历史版本列表"""
        return self._version_store.get(master_id, [])

    def rollback(self, master_id: int, target_version: int) -> Optional[Dict]:
        """回滚到指定版本"""
        versions = self._version_store.get(master_id, [])
        if target_version < 1 or target_version > len(versions):
            return None
        return copy.deepcopy(versions[target_version - 1])

    def can_transition(self, current_status: int, new_status: int) -> bool:
        """检查状态流转是否合法"""
        # 状态流转规则
        transitions = {
            0: [1, 5],        # 草稿 → 待审核 / 作废
            1: [2, 5],        # 待审核 → 已生成草稿 / 作废
            2: [3, 4, 5],     # 已生成草稿 → 部分上架 / 全部上架 / 作废
            3: [4, 5],        # 部分上架 → 全部上架 / 作废
            4: [5],           # 全部上架 → 作废
            5: [],            # 作废 → 不可流转
        }
        return new_status in transitions.get(current_status, [])

    def get_status_text(self, status: int) -> str:
        return self.STATUS_MAP.get(status, "未知")

    def generate_sku(self, prefix: str = "SKU") -> str:
        """生成唯一SKU"""
        import time
        ts = int(time.time() * 1000)
        return f"{prefix}-{ts}"


product_manager = ProductMasterManager()
print("[ProductMaster] Manager ready with version control.")
