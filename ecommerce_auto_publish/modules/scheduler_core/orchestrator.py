"""流水线编排器 — 全链路：抓取→合规闸→适配→草稿→审核→发布

v0.11.0: 优先使用浏览器自动化适配器（Playwright），失败时回退到 Mock 适配器
"""
import json
import time
import threading
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

HAS_BROWSER_AUTOMATION = False
try:
    from modules.adapter_layer.browser import get_browser_adapter
    HAS_BROWSER_AUTOMATION = True
except ImportError:
    pass


class TaskStatus(Enum):
    QUEUED = "queued"
    RUNNING = "running"
    PASSED = "passed"
    BLOCKED = "blocked"
    FAILED = "failed"
    PUBLISHED = "published"


@dataclass
class PipelineTask:
    """流水线任务"""
    task_id: str
    master_id: int
    platform: str
    status: TaskStatus = TaskStatus.QUEUED
    stage: str = ""
    result: Dict = field(default_factory=dict)
    error: str = ""
    draft_id: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self):
        return {
            "task_id": self.task_id,
            "master_id": self.master_id,
            "platform": self.platform,
            "status": self.status.value,
            "stage": self.stage,
            "draft_id": self.draft_id,
            "error": self.error,
            "result": self.result,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class PipelineOrchestrator:
    """全链路流水线编排器 — 线程池执行"""

    def __init__(self, max_workers: int = 4):
        self.tasks: Dict[str, PipelineTask] = {}
        self._counter = 0
        self._lock = threading.Lock()
        self._executor = None

    def _next_id(self, prefix: str = "TASK") -> str:
        self._counter += 1
        return f"{prefix}-{self._counter:06d}"

    def run_full_pipeline(self, master_data: Dict, platforms: List[str], db=None) -> Dict:
        """
        完整流水线执行：
        1. 三道闸校验
        2. 分别适配各平台
        3. 保存草稿
        4. 自动审核(模拟)
        5. 发布(模拟)
        """
        master_id = master_data.get("id", 0)
        results = {"master_id": master_id, "tasks": [], "summary": {}}

        # ===== Step 1: 三道闸 =====
        from modules.scheduler_core.task_dispatcher import dispatcher
        dispatch_result = dispatcher.dispatch(master_data, platforms)

        if not dispatch_result["passed"]:
            results["summary"] = {
                "total": len(platforms), "passed": 0,
                "blocked": len(platforms), "published": 0,
                "stage": dispatch_result["stage"],
                "errors": dispatch_result["errors"],
            }
            return results

        # ===== Step 2-6: 每个平台独立流水线 =====
        passed = 0
        blocked = 0  # compliance blocks only
        published = 0

        # Platform-specific configs
        platform_configs = {
            "taobao": {"shop_id": "default", "category_cid": "50010404"},
            "douyin": {"shop_id": "default", "category_id": "12345"},
            "pdd": {"shop_id": "default", "category_id": "67890"},
            "amazon": {"shop_id": "default", "category_id": "Fashion"},
        }

        for platform in platforms:
            task_id = self._next_id(f"{platform.upper()}")
            task = PipelineTask(
                task_id=task_id,
                master_id=master_id,
                platform=platform,
                status=TaskStatus.QUEUED,
                stage="start",
                created_at=datetime.utcnow().isoformat(),
            )

            try:
                # Step 2: 平台适配 (v0.11.0: 优先浏览器自动化)
                task.status = TaskStatus.RUNNING
                task.stage = "adapting"

                adapt_result = None
                adapter_used = "mock"

                # 尝试浏览器自动化适配器
                if HAS_BROWSER_AUTOMATION:
                    try:
                        print(f"[Orchestrator] 尝试浏览器自动化 → {platform}")
                        cfg = platform_configs.get(platform, {"shop_id": "default"})
                        browser_adapter = get_browser_adapter(platform, cfg)
                        adapt_result = browser_adapter.full_pipeline(master_data)
                        adapter_used = "browser"
                    except Exception as be:
                        print(f"[Orchestrator] 浏览器适配失败，回退到Mock: {be}")

                # 回退到 Mock API 适配器
                if adapt_result is None:
                    adapter_module = __import__(
                        f"modules.adapter_layer.{platform}_adapter",
                        fromlist=[f"{platform.capitalize()}Adapter"]
                    )
                    adapter_class = getattr(adapter_module, f"{platform.capitalize()}Adapter")
                    cfg = platform_configs.get(platform, {"shop_id": "default"})
                    adapter = adapter_class(cfg)
                    adapt_result = adapter.full_pipeline(master_data)
                    adapter_used = "mock"
                    print(f"[Orchestrator] 使用 Mock 适配器 → {platform}")

                if not adapt_result["success"]:
                    task.status = TaskStatus.FAILED
                    task.stage = "adapt_failed"
                    task.error = adapt_result.get("error", "适配失败")
                    task.result["adapter"] = adapter_used
                    self.tasks[task_id] = task
                    results["tasks"].append(task.to_dict())
                    continue

                task.draft_id = adapt_result["draft_id"]
                task.stage = "adapted"
                task.result["adapter"] = adapter_used
                passed += 1

                # Step 3: 保存草稿
                task.stage = "saving_draft"
                from modules.export_gate.publisher import publish_gate
                draft_id = publish_gate.drafts.save_draft(
                    platform, master_id,
                    {"title": master_data.get("title"), "draft_id": task.draft_id}
                )
                task.result["draft_id"] = draft_id
                task.stage = "draft_saved"

                # Step 4: 自动审核
                task.stage = "auditing"
                publish_gate.drafts.set_audit_status(draft_id, True)
                task.stage = "audit_passed"

                # Step 5: 发布
                task.stage = "publishing"
                can_pub, reason = publish_gate.can_publish("admin", platform, draft_id)
                if can_pub:
                    publish_gate.drafts.set_publish_status(draft_id, True)
                    task.status = TaskStatus.PUBLISHED
                    task.stage = "published"
                    published += 1

                    # 持久化平台关系
                    if db:
                        self._persist_platform_rel(db, master_id, platform, task)
                else:
                    task.stage = "publish_blocked"
                    task.error = reason

            except Exception as e:
                task.status = TaskStatus.FAILED
                task.stage = "error"
                task.error = str(e)

            task.updated_at = datetime.utcnow().isoformat()
            self.tasks[task_id] = task
            results["tasks"].append(task.to_dict())

        results["summary"] = {
            "total": len(platforms),
            "passed": passed,
            "blocked": len(platforms) - passed,
            "published": published,
            "stage": "complete",
            "errors": [],
        }

        return results

    def get_task(self, task_id: str) -> Optional[Dict]:
        task = self.tasks.get(task_id)
        return task.to_dict() if task else None

    def list_tasks(self, limit: int = 50) -> List[Dict]:
        tasks = list(self.tasks.values())
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        return [t.to_dict() for t in tasks[:limit]]


    def _persist_platform_rel(self, db, master_id: int, platform: str, task: PipelineTask):
        """持久化平台商品关系记录"""
        from db.models import ProductPlatformRel
        from datetime import datetime
        now = datetime.utcnow().isoformat()

        # Upsert: find existing or create new
        rel = db.query(ProductPlatformRel).filter(
            ProductPlatformRel.master_id == master_id,
            ProductPlatformRel.platform == platform,
        ).first()

        if rel:
            rel.platform_status = "published"
            rel.platform_draft_data = task.result
            rel.updated_at = now
        else:
            rel = ProductPlatformRel(
                master_id=master_id,
                platform=platform,
                shop_id="default",
                platform_status="published",
                platform_draft_data=task.result,
                platform_item_id=task.draft_id,
            )
            db.add(rel)
        db.commit()


# 全局单例
orchestrator = PipelineOrchestrator()
print("[Orchestrator] Pipeline ready.")
