"""Celery异步任务 — 抓取/图片处理/适配/发布"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tasks.celery_app import celery_app
from utils.retry_utils import CircuitBreaker

# 每个平台一个熔断器
circuit_breakers = {
    "taobao": CircuitBreaker("taobao"),
    "douyin": CircuitBreaker("douyin"),
    "pdd": CircuitBreaker("pdd"),
    "amazon": CircuitBreaker("amazon"),
}


@celery_app.task(bind=True, max_retries=3)
def crawl_task(self, source_url: str, platform: str = "1688"):
    """
    抓取任务：从1688抓取商品信息
    输入: source_url
    输出: 商品主表数据dict
    """
    print(f"[CrawlTask] 开始抓取: {source_url}")

    # MVP阶段：模拟抓取
    # TODO: 接入真实1688 API或爬虫
    try:
        # 模拟抓取结果
        product_data = {
            "title": f"抓取商品-{source_url[-30:]}",
            "desc": "这是从1688抓取的商品描述",
            "price": 99.0,
            "cost_price": 50.0,
            "stock": 500,
            "main_images": [],
            "source_url": source_url,
            "source_type": platform,
        }

        # 第一道闸：文字过滤
        from utils.text_filter import text_filter
        text_result = text_filter.scan_product(
            product_data["title"],
            product_data["desc"],
        )
        if not text_result["safe"]:
            print(f"[CrawlTask] 文字闸拦截: {text_result['hits']}")
            return {"status": "blocked", "reason": text_result["hits"]}

        print(f"[CrawlTask] 抓取成功: {product_data['title']}")
        return {"status": "success", "data": product_data}

    except Exception as e:
        print(f"[CrawlTask] 抓取失败: {e}")
        raise self.retry(exc=e, countdown=2 ** self.request.retries)


@celery_app.task(bind=True, max_retries=2)
def image_process_task(self, master_id: int, image_urls: list):
    """
    图片处理任务：下载 → 水印检测 → 格式转换
    输入: master_id + 图片URL列表
    """
    print(f"[ImageTask] 处理商品#{master_id}，共{len(image_urls)}张图片")

    processed = []
    for url in image_urls:
        # TODO: 实际下载和处理
        processed.append(f"processed_{url.split('/')[-1]}")

    print(f"[ImageTask] 处理完成: {len(processed)}张")
    return {"status": "success", "images": processed}


@celery_app.task(bind=True, max_retries=3)
def adapt_task(self, master_id: int, platform: str):
    """
    适配任务：读取主表 → 字段翻译 → 图片上传 → 提交草稿
    使用对应平台的适配器
    """
    print(f"[AdaptTask] 适配商品#{master_id} → {platform}")

    breaker = circuit_breakers.get(platform)
    if breaker and breaker.open:
        return {"status": "circuit_open", "message": f"{platform}平台熔断中"}

    try:
        # 动态加载适配器
        adapter_module = __import__(
            f"modules.adapter_layer.{platform}_adapter",
            fromlist=[f"{platform.capitalize()}Adapter"]
        )
        adapter_class = getattr(adapter_module, f"{platform.capitalize()}Adapter")
        adapter = adapter_class({"shop_id": "default"})

        # 模拟主表数据
        master_data = {
            "id": master_id,
            "inner_sku": f"SKU{master_id:06d}",
            "title": f"测试商品{master_id}",
            "price": 99.0,
            "stock": 100,
            "main_images": [],
        }

        result = adapter.full_pipeline(master_data)
        if result["success"]:
            print(f"[AdaptTask] {platform}适配成功，草稿ID: {result['draft_id']}")
            return {"status": "success", "draft_id": result["draft_id"]}
        else:
            print(f"[AdaptTask] {platform}适配失败: {result['error']}")
            return {"status": "failed", "error": result["error"]}

    except Exception as e:
        print(f"[AdaptTask] 异常: {e}")
        raise self.retry(exc=e, countdown=5)


@celery_app.task(bind=True, max_retries=2)
def publish_task(self, rel_id: int, platform: str):
    """
    发布任务：校验审核状态 → 调用平台发布
    """
    print(f"[PublishTask] 发布 #{rel_id} → {platform}")

    # TODO: 检查审核记录
    try:
        adapter_module = __import__(
            f"modules.adapter_layer.{platform}_adapter",
            fromlist=[f"{platform.capitalize()}Adapter"]
        )
        adapter_class = getattr(adapter_module, f"{platform.capitalize()}Adapter")
        adapter = adapter_class({"shop_id": "default"})

        success = adapter.publish_draft(str(rel_id))
        return {"status": "success" if success else "failed"}

    except Exception as e:
        print(f"[PublishTask] 失败: {e}")
        raise self.retry(exc=e)


print("[PipelineTasks] crawl_task, image_process_task, adapt_task, publish_task registered.")
