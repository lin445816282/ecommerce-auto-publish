"""全平台AI自动上架系统 — FastAPI入口"""
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from db.session import init_db, get_db, redis_client
from db.models import ProductMaster, ProductPlatformRel, TaskJob, AuditRecord
from sqlalchemy.orm import Session

app = FastAPI(
    title="全平台AI自动上架系统",
    description="支持淘宝/天猫/抖店/拼多多/亚马逊的多平台AI自动上架",
    version="0.1.0",
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
    """抓取1688商品信息，生成主表记录"""
    # MVP阶段返回模拟数据
    master = ProductMaster(
        inner_sku=f"CRW_{datetime.utcnow().timestamp():.0f}",
        title=f"商品-{req.source_url[-20:]}",
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


@app.post("/api/publish/execute/{rel_id}", tags=["发布"])
async def publish_execute(rel_id: int, db: Session = Depends(get_db)):
    """发布门：必须审核通过才允许发布"""
    rel = db.query(ProductPlatformRel).filter(ProductPlatformRel.id == rel_id).first()
    if not rel:
        raise HTTPException(404, "记录不存在")

    # 检查是否审核通过
    audit = db.query(AuditRecord).filter(
        AuditRecord.master_id == rel.master_id,
        AuditRecord.platform == rel.platform,
        AuditRecord.audit_result == 1,
    ).first()

    if not audit:
        raise HTTPException(403, "未通过审核，无法发布")

    # TODO: 调用对应平台adapter.publish_draft()
    rel.platform_status = "published"
    db.commit()
    return {"code": 0, "msg": f"已发布到{rel.platform}"}


# ============ 启动 ============

@app.on_event("startup")
async def startup():
    print("=" * 50)
    print("  全平台AI自动上架系统 v0.1.0")
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
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
    }

