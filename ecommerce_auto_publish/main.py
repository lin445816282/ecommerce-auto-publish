"""全平台AI自动上架系统 — FastAPI入口 v0.4.0"""
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import base64

from db.session import init_db, get_db
from db.models import ProductMaster, ProductPlatformRel, TaskJob, AuditRecord
from sqlalchemy.orm import Session

from modules.product_source.crawler import product_importer
from modules.product_master.manager import product_manager as pm_mgr
from modules.scheduler_core.task_dispatcher import dispatcher
from modules.scheduler_core.orchestrator import orchestrator
from modules.export_gate.publisher import publish_gate, PublishPermission
from modules.ai_brain.engine import ai_engine
from modules.ai_brain.config_manager import ai_config
from modules.ai_brain.image_processor import image_processor as img_proc

app = FastAPI(
    title="全平台AI自动上架系统",
    description="支持淘宝/天猫/抖店/拼多多/亚马逊的多平台AI自动上架",
    version="0.4.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ 产品源模块 ============

class CrawlRequest(BaseModel):
    source_url: str
    platform: str = "1688"


class PublishRequest(BaseModel):
    draft_id: str
    platform: str
    user_id: str = "admin"


class ManualProductRequest(BaseModel):
    inner_sku: str
    title: str
    price: float
    cost_price: float = 0.0
    stock: int = 0
    desc: str = ""
    main_images: List[str] = []
    attrs: dict = {}


@app.post("/api/product/crawl", tags=["产品源"])
async def crawl_product(req: CrawlRequest, db: Session = Depends(get_db)):
    """抓取1688商品信息 → 文字闸 → 入库"""
    # Step 1: 抓取
    result = product_importer.import_from_1688(req.source_url)
    if not result["success"]:
        raise HTTPException(400, f"抓取失败: {result.get('error', '未知错误')}")

    data = result["data"]

    # Step 2: 文字闸
    from utils.text_filter import text_filter
    text_result = text_filter.scan_product(data.get("title", ""), data.get("desc", ""))
    if not text_result["safe"]:
        # 入库但标记作废
        master = ProductMaster(
            inner_sku=data["inner_sku"],
            title=data.get("title", ""),
            desc=data.get("desc", ""),
            price=data.get("price", 0),
            cost_price=data.get("wholesale_price", 0),
            stock=data.get("stock", 0),
            main_images=data.get("main_images", []),
            detail_images=data.get("detail_images", []),
            spec_json=data.get("spec_json", {}),
            attrs_json=data.get("attrs_json", {}),
            source_type="1688",
            source_url=req.source_url,
            status=5,  # 作废
        )
        db.add(master)
        db.commit()
        return {
            "code": 0,
            "data": {"master_id": master.id, "status": 5},
            "warning": f"商品被文字闸拦截: {text_result['hits']}",
        }

    # Step 3: 正常入库
    master = ProductMaster(
        inner_sku=data["inner_sku"],
        title=data.get("title", ""),
        desc=data.get("desc", ""),
        price=data.get("price", 0),
        cost_price=data.get("wholesale_price", 0),
        stock=data.get("stock", 0),
        main_images=data.get("main_images", []),
        detail_images=data.get("detail_images", []),
        spec_json=data.get("spec_json", {}),
        attrs_json=data.get("attrs_json", {}),
        source_type="1688",
        source_url=req.source_url,
        status=0,
    )
    db.add(master)
    db.commit()
    db.refresh(master)
    return {"code": 0, "data": {"master_id": master.id, "inner_sku": master.inner_sku}}


@app.post("/api/product/manual/create", tags=["产品源"])
async def manual_create(req: ManualProductRequest, db: Session = Depends(get_db)):
    """手动录入商品"""
    master = ProductMaster(
        inner_sku=req.inner_sku,
        title=req.title,
        desc=req.desc,
        price=req.price,
        cost_price=req.cost_price,
        stock=req.stock,
        main_images=req.main_images,
        attrs_json=req.attrs,
        source_type="manual",
        status=0,
    )
    db.add(master)
    db.commit()
    db.refresh(master)
    return {"code": 0, "data": {"master_id": master.id}}


@app.get("/api/product/master/list", tags=["产品源"])
async def product_list(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    """商品主列表"""
    items = db.query(ProductMaster).offset(skip).limit(limit).all()
    return {"code": 0, "data": [{"id": i.id, "title": i.title, "status": i.status, "price": i.price} for i in items]}


@app.get("/api/product/master/{pid}", tags=["产品源"])
async def product_detail(pid: int, db: Session = Depends(get_db)):
    """获取单条主商品详情"""
    master = db.query(ProductMaster).filter(ProductMaster.id == pid).first()
    if not master:
        raise HTTPException(404, "商品不存在")
    return {"code": 0, "data": {
        "id": master.id, "inner_sku": master.inner_sku, "title": master.title,
        "desc": master.desc, "price": master.price, "stock": master.stock,
        "images": master.main_images, "attrs": master.attrs_json,
        "status": master.status, "version": master.version,
    }}


# ============ 调度核心模块 ============

@app.post("/api/task/create", tags=["调度"])
async def create_task(job_type: str, master_id: int, platform: str, db: Session = Depends(get_db)):
    """创建任务"""
    task = TaskJob(
        job_type=job_type,
        master_id=master_id,
        platform=platform,
        job_status=0,
    )
    db.add(task)
    db.commit()
    return {"code": 0, "data": {"task_id": task.id}}


@app.get("/api/task/list", tags=["调度"])
async def task_list(db: Session = Depends(get_db)):
    """任务列表"""
    tasks = db.query(TaskJob).order_by(TaskJob.create_time.desc()).limit(50).all()
    return {"code": 0, "data": [{"id": t.id, "type": t.job_type, "status": t.job_status} for t in tasks]}


@app.post("/api/product/dispatch/{master_id}", tags=["调度"])
async def dispatch_product(master_id: int, platforms: str = "taobao,douyin", db: Session = Depends(get_db)):
    """商品分发：经过三道闸校验，分发到指定平台"""
    master = db.query(ProductMaster).filter(ProductMaster.id == master_id).first()
    if not master:
        raise HTTPException(404, "商品不存在")

    if master.status == 5:
        raise HTTPException(400, "商品已作废，无法分发")

    # 构建分发数据
    master_data = {
        "id": master.id,
        "inner_sku": master.inner_sku,
        "title": master.title,
        "desc": master.desc,
        "price": master.price,
        "cost_price": master.cost_price,
        "main_images": master.main_images,
        "attrs_json": master.attrs_json,
    }

    # 执行三道闸 + 分发
    platform_list = [p.strip() for p in platforms.split(",")]
    result = dispatcher.dispatch(master_data, platform_list)

    # 根据结果更新商品状态
    if not result["passed"]:
        if result["stage"] == "text_filter_blocked":
            master.status = 5
        elif result["stage"] == "price_check_blocked":
            master.status = 1  # 待审核
        db.commit()

    return {"code": 0, "data": result}


# ============ 全链路流水线（一键执行） ============

class PipelineRequest(BaseModel):
    master_id: int
    platforms: str = "taobao,douyin"


@app.post("/api/pipeline/run", tags=["流水线"])
async def run_pipeline(req: PipelineRequest, db: Session = Depends(get_db)):
    """一键全链路：抓取→审核→适配→草稿→发布"""
    master = db.query(ProductMaster).filter(ProductMaster.id == req.master_id).first()
    if not master:
        raise HTTPException(404, "商品不存在")
    if master.status == 5:
        raise HTTPException(400, "商品已作废")

    master_data = {
        "id": master.id, "inner_sku": master.inner_sku,
        "title": master.title, "desc": master.desc,
        "price": master.price, "cost_price": master.cost_price,
        "main_images": master.main_images, "attrs_json": master.attrs_json,
    }

    platforms = [p.strip() for p in req.platforms.split(",")]
    result = orchestrator.run_full_pipeline(master_data, platforms)

    # 更新商品状态
    summary = result["summary"]
    if summary.get("stage") == "text_filter_blocked":
        master.status = 5  # 文字违规→作废
    elif summary.get("stage") == "price_check_blocked":
        master.status = 1  # 价格异常→待审核
    elif summary["published"] > 0:
        master.status = 3 if summary["published"] < summary["total"] else 4  # 部分/全部上架
    # adapter failures leave status unchanged
    db.commit()

    return {"code": 0, "data": result}


@app.get("/api/pipeline/tasks", tags=["流水线"])
async def list_pipeline_tasks():
    """流水线任务列表"""
    return {"code": 0, "data": orchestrator.list_tasks()}


@app.get("/api/pipeline/task/{task_id}", tags=["流水线"])
async def get_pipeline_task(task_id: str):
    """查看单个流水线任务"""
    task = orchestrator.get_task(task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    return {"code": 0, "data": task}


# ============ AI决策层 ============

class AIAuditRequest(BaseModel):
    title: str
    desc: str = ""
    attrs: dict = {}


class AITitleRequest(BaseModel):
    product_info: dict
    platform: str = "通用"


class AIDescRequest(BaseModel):
    title: str
    desc: str = ""
    attrs: dict = {}


class AIKeywordsRequest(BaseModel):
    title: str
    desc: str = ""


@app.post("/api/ai/audit", tags=["AI决策"])
async def ai_audit(req: AIAuditRequest):
    """AI智能审核商品"""
    result = ai_engine.audit_product(req.title, req.desc, req.attrs)
    return {"code": 0, "data": result}


@app.post("/api/ai/gen_title", tags=["AI决策"])
async def ai_gen_title(req: AITitleRequest):
    """AI生成商品标题（返回3个版本）"""
    result = ai_engine.generate_titles(req.product_info, req.platform)
    return {"code": 0, "data": result}


@app.post("/api/ai/optimize_desc", tags=["AI决策"])
async def ai_optimize_desc(req: AIDescRequest):
    """AI优化商品描述"""
    result = ai_engine.optimize_description(req.title, req.desc, req.attrs)
    return {"code": 0, "data": result}


@app.post("/api/ai/keywords", tags=["AI决策"])
async def ai_extract_keywords(req: AIKeywordsRequest):
    """AI提取热搜关键词"""
    keywords = ai_engine.extract_keywords(req.title, req.desc)
    return {"code": 0, "data": {"keywords": keywords}}


# ============ AI配置管理 ============

class AIKeyRequest(BaseModel):
    api_key: str

class AIProviderRequest(BaseModel):
    provider: str  # openai / claude

class AIModelRequest(BaseModel):
    model: str


@app.get("/api/ai/config", tags=["AI配置"])
async def get_ai_config():
    """获取当前AI配置（Key脱敏）"""
    return {"code": 0, "data": ai_config.get_config()}


@app.post("/api/ai/config/key", tags=["AI配置"])
async def set_ai_key(req: AIKeyRequest):
    """设置API Key"""
    return {"code": 0, "data": ai_config.set_api_key(req.api_key)}


@app.post("/api/ai/config/provider", tags=["AI配置"])
async def set_ai_provider(req: AIProviderRequest):
    """切换AI提供商（openai/claude）"""
    return {"code": 0, "data": ai_config.set_provider(req.provider)}


@app.post("/api/ai/config/model", tags=["AI配置"])
async def set_ai_model(req: AIModelRequest):
    """设置模型名称"""
    return {"code": 0, "data": ai_config.set_model(req.model)}


@app.post("/api/ai/config/test", tags=["AI配置"])
async def test_ai_connection():
    """测试AI连接是否正常"""
    return {"code": 0, "data": ai_config.test_connection()}


# ============ AI图片处理 ============

class ImageProcessRequest(BaseModel):
    operations: List[str] = ["remove_bg", "watermark", "optimize"]
    watermark_text: str = ""
    platform: str = "taobao"


@app.post("/api/image/process", tags=["AI图片处理"])
async def process_image(
    file: UploadFile = File(...),
    operations: str = "remove_bg,watermark,optimize",
    watermark_text: str = "",
    platform: str = "taobao",
):
    """上传图片 → AI抠图/水印/平台优化 → 返回base64预览"""
    ops = [o.strip() for o in operations.split(",") if o.strip()]
    image_data = await file.read()
    result = img_proc.process_image(image_data, ops, watermark_text, platform)
    if not result.get("ok"):
        raise HTTPException(400, result.get("error", "处理失败"))
    return {"code": 0, "data": result}


@app.post("/api/image/batch", tags=["AI图片处理"])
async def batch_process_images(
    files: List[UploadFile] = File(...),
    operations: str = "remove_bg,watermark,optimize",
    watermark_text: str = "",
    platform: str = "taobao",
):
    """批量上传图片处理"""
    ops = [o.strip() for o in operations.split(",") if o.strip()]
    results = []
    for file in files:
        image_data = await file.read()
        result = img_proc.process_image(image_data, ops, watermark_text, platform)
        results.append({"filename": file.filename, **result})
    return {"code": 0, "data": results}


@app.get("/api/image/specs", tags=["AI图片处理"])
async def get_image_specs():
    """获取各平台图片规范"""
    from modules.ai_brain.image_processor import PLATFORM_SPECS
    return {"code": 0, "data": PLATFORM_SPECS}


# ============ 出口（审核发布） ============

@app.get("/api/audit/pending/list", tags=["审核"])
async def pending_audit(db: Session = Depends(get_db)):
    """待审核草稿列表"""
    rels = db.query(ProductPlatformRel).filter(
        ProductPlatformRel.platform_status == "pending_audit"
    ).all()
    return {"code": 0, "data": [{"id": r.id, "master_id": r.master_id, "platform": r.platform} for r in rels]}


@app.post("/api/audit/submit", tags=["审核"])
async def submit_audit(rel_id: int, approved: bool, comment: str = "", db: Session = Depends(get_db)):
    """审核通过/驳回"""
    rel = db.query(ProductPlatformRel).filter(ProductPlatformRel.id == rel_id).first()
    if not rel:
        raise HTTPException(404, "记录不存在")

    audit = AuditRecord(
        master_id=rel.master_id,
        platform=rel.platform,
        audit_type="manual",
        audit_result=1 if approved else 2,
        audit_comment=comment,
    )
    db.add(audit)

    if approved:
        rel.platform_status = "draft"  # 审核通过，等待发布
    else:
        rel.platform_status = "fail"
        rel.error_msg = comment

    db.commit()
    return {"code": 0, "msg": "审核完成"}


@app.post("/api/publish/execute", tags=["发布"])
async def publish_execute(req: PublishRequest):
    """发布门：三重校验（权限+审核+不重复）"""
    can_pub, reason = publish_gate.can_publish(req.user_id, req.platform, req.draft_id)
    if not can_pub:
        raise HTTPException(403, reason)

    # 调用平台适配器发布
    try:
        adapter_module = __import__(
            f"modules.adapter_layer.{req.platform}_adapter",
            fromlist=[f"{req.platform.capitalize()}Adapter"]
        )
        adapter_class = getattr(adapter_module, f"{req.platform.capitalize()}Adapter")
        adapter = adapter_class({"shop_id": "default"})
        success = adapter.publish_draft(req.draft_id)

        if success:
            publish_gate.drafts.set_publish_status(req.draft_id, True)
            return {"code": 0, "msg": f"已发布到{req.platform}", "draft_id": req.draft_id}
        else:
            publish_gate.drafts.set_publish_status(req.draft_id, False, "平台返回失败")
            raise HTTPException(500, "平台发布失败")
    except ImportError:
        raise HTTPException(400, f"不支持的平台: {req.platform}")


@app.get("/api/publish/status/{draft_id}", tags=["发布"])
async def publish_status(draft_id: str):
    """查询发布状态"""
    draft = publish_gate.drafts.get_draft(draft_id)
    if not draft:
        raise HTTPException(404, "草稿不存在")
    return {"code": 0, "data": draft}


# ============ 启动 ============

@app.on_event("startup")
async def startup():
    print("=" * 50)
    print("  全平台AI自动上架系统 v0.4.0")
    print("  六层架构 · FastAPI后端")
    print("=" * 50)
    try:
        init_db()
        print("[Startup] 数据库初始化完成")
    except Exception as e:
        print(f"[Startup] 数据库未连接(开发模式): {e}")
    print("[Startup] 系统就绪，访问 http://localhost:8000/docs 查看API文档")


@app.get("/")
async def root():
    return {
        "name": "全平台AI自动上架系统",
        "version": "0.4.0",
        "status": "running",
        "docs": "/docs",
    }

