"""Celery 应用配置"""
from celery import Celery
from config.settings import REDIS_URL

celery_app = Celery(
    "ecommerce_auto_publish",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

print("[Celery] App configured.")
