"""调度核心 — 任务分发器：将商品流转经过三道闸，分发到各平台适配器"""
import json
from typing import Dict, List, Optional
from datetime import datetime

from utils.text_filter import text_filter
from utils.image_check import image_checker


class TaskDispatcher:
    """任务调度器：接收主商品，执行合规检查，分发到平台适配器"""

    def __init__(self):
        self.pipeline_steps = []

    def dispatch(self, master_data: Dict, platforms: List[str]) -> Dict:
        """
        完整调度流水线：
        1. 文字闸 → 违规直接作废
        2. 图片闸 → 水印/侵权拦截
        3. 业务校验 → 价格异常拦截
        4. 分发到各平台适配器
        """
        result = {
            "master_id": master_data.get("id"),
            "passed": False,
            "stage": "start",
            "errors": [],
            "platform_results": {},
            "timestamp": datetime.utcnow().isoformat(),
        }

        # ===== 第一道闸：文字违规检测 =====
        title = master_data.get("title", "")
        desc = master_data.get("desc", "")
        attrs = master_data.get("attrs_json", {})

        text_result = text_filter.scan_product(title, desc, attrs)
        if not text_result["safe"]:
            result["stage"] = "text_filter_blocked"
            result["errors"].append({
                "type": "TEXT_BAN",
                "details": text_result["hits"],
            })
            # 标记商品作废
            result["status_code"] = 5  # 作废
            return result

        result["stage"] = "text_filter_passed"

        # ===== 第二道闸：图片检测 =====
        images = master_data.get("main_images", [])
        if images:
            img_result = image_checker.full_check(images)
            if not img_result["all_clear"]:
                result["stage"] = "image_check_blocked"
                result["errors"].append({
                    "type": "IMAGE_BAN",
                    "watermark": img_result["watermark_images"],
                    "brand": img_result["brand_images"],
                })
                return result

        result["stage"] = "image_check_passed"

        # ===== 第三道闸：业务校验 =====
        price = float(master_data.get("price", 0))
        cost_price = float(master_data.get("cost_price", 0))
        if cost_price > 0 and price < cost_price * 0.3:
            result["stage"] = "price_check_blocked"
            result["errors"].append({
                "type": "PRICE_ANOMALY",
                "price": price,
                "cost": cost_price,
                "reason": f"售价({price})低于成本({cost_price})的30%，进入人工审核",
            })
            return result

        result["stage"] = "business_check_passed"

        # ===== 第四步：分发到各平台 =====
        result["passed"] = True
        result["stage"] = "dispatched"

        for platform in platforms:
            result["platform_results"][platform] = {
                "status": "queued",
                "message": f"已加入{platform}适配队列",
            }

        return result


# 全局单例
dispatcher = TaskDispatcher()
print("[TaskDispatcher] Ready.")
