"""出口层 — 草稿管理 + 发布权限 + 渠道分发"""
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum


class PublishPermission(Enum):
    """发布权限级别"""
    VIEW = 0        # 只能查看
    DRAFT = 1       # 可保存草稿
    AUDIT = 2       # 可审核
    PUBLISH = 3     # 可发布
    ADMIN = 4       # 全部权限


class DraftManager:
    """草稿管理器"""

    def __init__(self):
        self._drafts = {}  # draft_id -> draft data

    def save_draft(self, platform: str, master_id: int, payload: Dict) -> str:
        """保存草稿"""
        draft_id = f"{platform}_draft_{master_id}_{int(datetime.utcnow().timestamp())}"
        self._drafts[draft_id] = {
            "draft_id": draft_id,
            "platform": platform,
            "master_id": master_id,
            "payload": payload,
            "status": "draft",
            "created_at": datetime.utcnow().isoformat(),
            "audit_status": None,
            "publish_status": None,
        }
        return draft_id

    def get_draft(self, draft_id: str) -> Optional[Dict]:
        return self._drafts.get(draft_id)

    def set_audit_status(self, draft_id: str, approved: bool, comment: str = ""):
        draft = self._drafts.get(draft_id)
        if draft:
            draft["audit_status"] = "approved" if approved else "rejected"
            draft["audit_comment"] = comment
            draft["status"] = "pending_publish" if approved else "rejected"

    def set_publish_status(self, draft_id: str, success: bool, error: str = ""):
        draft = self._drafts.get(draft_id)
        if draft:
            draft["publish_status"] = "published" if success else "failed"
            draft["publish_error"] = error
            draft["status"] = "published" if success else "publish_failed"


class PublishGate:
    """发布门 — 必须校验权限 + 审核状态"""

    def __init__(self):
        self._permissions = {}  # user_id -> {platform: PublishPermission}
        self.drafts = DraftManager()

    def set_permission(self, user_id: str, platform: str, level: PublishPermission):
        """设置用户权限"""
        if user_id not in self._permissions:
            self._permissions[user_id] = {}
        self._permissions[user_id][platform] = level

    def check_permission(self, user_id: str, platform: str, required: PublishPermission) -> bool:
        """检查用户是否有足够权限"""
        user_perm = self._permissions.get(user_id, {}).get(platform)
        if user_perm is None:
            return False
        return user_perm.value >= required.value

    def can_publish(self, user_id: str, platform: str, draft_id: str) -> tuple:
        """
        发布前置校验
        返回: (can_publish: bool, reason: str)
        """
        # 1. 权限检查
        if not self.check_permission(user_id, platform, PublishPermission.PUBLISH):
            return False, f"用户 {user_id} 无 {platform} 发布权限"

        # 2. 审核状态检查
        draft = self.drafts.get_draft(draft_id)
        if not draft:
            return False, f"草稿 {draft_id} 不存在"

        if draft.get("audit_status") != "approved":
            return False, f"草稿 {draft_id} 未通过审核"

        # 3. 防止重复发布
        if draft.get("publish_status") == "published":
            return False, f"草稿 {draft_id} 已发布，不可重复"

        return True, "OK"


publish_gate = PublishGate()

# 初始化默认权限 — 4平台全部授权
for _plat in ["taobao", "douyin", "pdd", "amazon"]:
    publish_gate.set_permission("admin", _plat, PublishPermission.ADMIN)
    publish_gate.set_permission("operator", _plat, PublishPermission.DRAFT)

print("[ExportGate] PublishGate + DraftManager ready.")
