"""全平台AI自动上架系统 — FastAPI入口 v0.7.0 (JWT Auth)"""
import csv
import io
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import base64

from db.session import init_db, get_db
from db.models import ProductMaster, ProductPlatformRel, TaskJob, AuditRecord, User
from sqlalchemy.orm import Session

from modules.product_source.crawler import product_importer
from modules.product_master.manager import product_manager as pm_mgr
from modules.scheduler_core.task_dispatcher import dispatcher
from modules.scheduler_core.orchestrator import orchestrator
from modules.export_gate.publisher import publish_gate, PublishPermission
import modules.ai_brain.engine as ai_engine_mod  # module ref for hot-reload
from modules.ai_brain.config_manager import ai_config
from modules.ai_brain.image_processor import image_processor as img_proc
from modules.auth.jwt_handler import (
    hash_password, verify_password, create_access_token, create_refresh_token,
    decode_token, require_auth, optional_auth, bearer_scheme,
)

app = FastAPI(
    title="全平台AI自动上架系统",
    description="支持淘宝/天猫/抖店/拼多多/亚马逊的多平台AI自动上架",
    version="0.5.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ 认证模块 (JWT) ============

class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    full_name: str = ""


class RefreshRequest(BaseModel):
    refresh_token: str


def get_current_user(
    credentials=Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """从JWT token获取当前登录用户"""
    if credentials is None:
        raise HTTPException(401, "未提供认证令牌")
    payload = decode_token(credentials.credentials)
    if payload is None:
        raise HTTPException(401, "令牌无效或已过期")
    if payload.get("type") != "access":
        raise HTTPException(401, "请使用access token")
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user or not user.is_active:
        raise HTTPException(401, "用户不存在或已禁用")
    return user


@app.post("/api/auth/login", tags=["认证"])
async def login(req: LoginRequest, db: Session = Depends(get_db)):
    """用户登录，返回 access_token + refresh_token"""
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(401, "用户名或密码错误")
    if not user.is_active:
        raise HTTPException(403, "账户已被禁用")

    user.last_login = datetime.utcnow()
    db.commit()

    access_token = create_access_token(user.id, user.username, user.role)
    refresh_token = create_refresh_token(user.id)

    return {
        "code": 0,
        "data": {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "username": user.username,
                "full_name": user.full_name,
                "role": user.role,
            },
        },
    }


@app.post("/api/auth/register", tags=["认证"])
async def register(req: RegisterRequest, db: Session = Depends(get_db)):
    """注册新用户（默认operator角色）"""
    existing = db.query(User).filter(User.username == req.username).first()
    if existing:
        raise HTTPException(400, "用户名已存在")

    if len(req.password) < 6:
        raise HTTPException(400, "密码至少6位")

    user = User(
        username=req.username,
        password_hash=hash_password(req.password),
        full_name=req.full_name or req.username,
        role="operator",
        is_active=1,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return {"code": 0, "data": {"id": user.id, "username": user.username, "message": "注册成功"}}


@app.post("/api/auth/refresh", tags=["认证"])
async def refresh_token(req: RefreshRequest):
    """刷新 access_token"""
    payload = decode_token(req.refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(401, "refresh_token无效或已过期")

    access_token = create_access_token(
        int(payload["sub"]), payload.get("username", ""), payload.get("role", "operator")
    )
    return {"code": 0, "data": {"access_token": access_token, "token_type": "bearer"}}


@app.get("/api/auth/me", tags=["认证"])
async def get_me(user: User = Depends(get_current_user)):
    """获取当前登录用户信息"""
    return {
        "code": 0,
        "data": {
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "role": user.role,
            "last_login": user.last_login.isoformat() if user.last_login else None,
        },
    }


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
async def crawl_product(req: CrawlRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
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
async def manual_create(req: ManualProductRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
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


# --- 批量CSV导入 ---

CSV_COLUMN_MAP = {
    "sku": "inner_sku", "商品编码": "inner_sku", "inner_sku": "inner_sku",
    "title": "title", "标题": "title", "商品名称": "title",
    "price": "price", "售价": "price", "价格": "price",
    "cost_price": "cost_price", "成本": "cost_price", "成本价": "cost_price",
    "stock": "stock", "库存": "stock",
    "desc": "desc", "描述": "desc", "详情": "desc",
}


@app.post("/api/product/import/csv", tags=["产品源"])
async def import_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """批量导入CSV商品"""
    if not file.filename or not file.filename.endswith('.csv'):
        raise HTTPException(400, "请上传.csv文件")

    content = await file.read()
    try:
        text = content.decode("utf-8-sig")  # handle BOM
    except UnicodeDecodeError:
        text = content.decode("gbk", errors="replace")

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(400, "CSV为空或无标题行")

    # Auto-detect column mapping
    mapping = {}
    for col in reader.fieldnames:
        col_clean = col.strip()
        field = CSV_COLUMN_MAP.get(col_clean, CSV_COLUMN_MAP.get(col_clean.lower(), None))
        if field:
            mapping[col] = field

    imported, skipped, errors = 0, 0, []
    seen_skus = set()  # track SKUs within this batch (not yet committed)
    for row_idx, row in enumerate(reader, start=1):
        data = {}
        for csv_col, db_field in mapping.items():
            val = row.get(csv_col, "").strip()
            if val:
                data[db_field] = val

        sku = data.get("inner_sku", "")
        title = data.get("title", "")
        price_str = data.get("price", "0")

        if not title:
            skipped += 1
            errors.append({"row": row_idx, "error": "缺少标题"})
            continue

        if not sku:
            sku = f"IMP-{int(datetime.utcnow().timestamp())}-{row_idx}"
            data["inner_sku"] = sku

        # Check duplicate SKU (both in-DB and in-batch)
        if sku in seen_skus:
            skipped += 1
            errors.append({"row": row_idx, "sku": sku, "error": "SKU重复(同批次)"})
            continue

        existing = db.query(ProductMaster).filter(ProductMaster.inner_sku == sku).first()
        if existing:
            skipped += 1
            errors.append({"row": row_idx, "sku": sku, "error": "SKU重复"})
            continue

        seen_skus.add(sku)

        try:
            price = float(price_str) if price_str else 0.0
            cost_price = float(data.get("cost_price", 0)) if data.get("cost_price") else 0.0
            stock = int(data.get("stock", 0)) if data.get("stock") else 0

            master = ProductMaster(
                inner_sku=sku,
                title=title,
                desc=data.get("desc", ""),
                price=price,
                cost_price=cost_price,
                stock=stock,
                source_type="csv_import",
                status=0,
            )
            db.add(master)
            imported += 1
        except (ValueError, TypeError) as e:
            skipped += 1
            errors.append({"row": row_idx, "sku": sku, "error": str(e)})

    db.commit()

    return {
        "code": 0,
        "data": {
            "imported": imported,
            "skipped": skipped,
            "total": imported + skipped,
            "errors": errors[:20],  # cap error list
        },
    }


# --- 全文搜索 ---

@app.get("/api/product/search", tags=["产品源"])
async def search_products(
    q: str = "",
    status: Optional[int] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """全文搜索商品（标题+SKU）"""
    query = db.query(ProductMaster)
    if q:
        pattern = f"%{q}%"
        query = query.filter(
            ProductMaster.title.like(pattern) | ProductMaster.inner_sku.like(pattern)
        )
    if status is not None:
        query = query.filter(ProductMaster.status == status)

    total = query.count()
    items = query.order_by(ProductMaster.id.desc()).offset(skip).limit(limit).all()

    return {
        "code": 0,
        "data": {
            "total": total,
            "items": [
                {"id": i.id, "inner_sku": i.inner_sku, "title": i.title,
                 "price": i.price, "stock": i.stock, "status": i.status,
                 "source_type": i.source_type, "create_time": i.create_time.isoformat() if i.create_time else None}
                for i in items
            ],
        },
    }


# --- CSV导出 ---

@app.get("/api/product/export/csv", tags=["产品源"])
async def export_csv(
    status: Optional[int] = None,
    platform: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """导出商品为CSV"""
    query = db.query(ProductMaster)
    if status is not None:
        query = query.filter(ProductMaster.status == status)

    items = query.order_by(ProductMaster.id).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "SKU", "标题", "售价", "成本价", "库存", "状态", "来源", "创建时间"])

    STATUS_LABELS_MAP = {0: "草稿", 1: "待审核", 2: "已生成草稿", 3: "部分上架", 4: "全部上架", 5: "作废"}

    for item in items:
        writer.writerow([
            item.id, item.inner_sku, item.title, item.price, item.cost_price,
            item.stock, STATUS_LABELS_MAP.get(item.status, str(item.status)),
            item.source_type, item.create_time.isoformat() if item.create_time else "",
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=products_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"},
    )


# --- 商品编辑 & 删除 ---

class UpdateProductRequest(BaseModel):
    title: Optional[str] = None
    price: Optional[float] = None
    cost_price: Optional[float] = None
    stock: Optional[int] = None
    desc: Optional[str] = None
    main_images: Optional[list] = None
    attrs_json: Optional[dict] = None


@app.put("/api/product/master/{pid}", tags=["产品源"])
async def update_product(
    pid: int,
    req: UpdateProductRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """更新商品信息（增量更新，仅传需修改的字段）"""
    master = db.query(ProductMaster).filter(ProductMaster.id == pid).first()
    if not master:
        raise HTTPException(404, "商品不存在")

    changed = False
    fields = {
        "title": req.title, "price": req.price, "cost_price": req.cost_price,
        "stock": req.stock, "desc": req.desc,
        "main_images": req.main_images, "attrs_json": req.attrs_json,
    }
    for field, value in fields.items():
        if value is not None:
            setattr(master, field, value)
            changed = True

    if changed:
        master.version = (master.version or 0) + 1
        master.update_time = datetime.utcnow()
        db.commit()
        db.refresh(master)

    return {"code": 0, "data": {"id": master.id, "version": master.version, "updated": changed}}


@app.delete("/api/product/master/{pid}", tags=["产品源"])
async def delete_product(
    pid: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """删除商品（仅admin可操作）"""
    if user.role != "admin":
        raise HTTPException(403, "仅管理员可删除商品")

    master = db.query(ProductMaster).filter(ProductMaster.id == pid).first()
    if not master:
        raise HTTPException(404, "商品不存在")

    # 删除关联的平台关系
    db.query(ProductPlatformRel).filter(ProductPlatformRel.master_id == pid).delete()
    db.delete(master)
    db.commit()

    return {"code": 0, "data": {"deleted": pid, "inner_sku": master.inner_sku}}


# --- 批量发布 ---

class BatchPublishRequest(BaseModel):
    master_ids: List[int]
    platforms: str = "taobao,douyin,pdd,amazon"


@app.post("/api/product/batch_publish", tags=["产品源"])
async def batch_publish(
    req: BatchPublishRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """批量发布：选中多个商品，一键全平台发布"""
    platforms = [p.strip() for p in req.platforms.split(",")]
    results = []

    for mid in req.master_ids:
        master = db.query(ProductMaster).filter(ProductMaster.id == mid).first()
        if not master:
            results.append({"master_id": mid, "status": "not_found"})
            continue
        if master.status == 5:
            results.append({"master_id": mid, "title": master.title, "status": "void"})
            continue

        master_data = {
            "id": master.id, "inner_sku": master.inner_sku,
            "title": master.title, "desc": master.desc,
            "price": master.price, "cost_price": master.cost_price,
            "main_images": master.main_images, "attrs_json": master.attrs_json,
        }

        pipe_result = orchestrator.run_full_pipeline(master_data, platforms, db=db)
        summary = pipe_result["summary"]

        # Update product status
        if summary.get("stage") == "text_filter_blocked":
            master.status = 5
        elif summary.get("stage") == "price_check_blocked":
            master.status = 1
        elif summary["published"] > 0:
            master.status = 3 if summary["published"] < summary["total"] else 4

        results.append({
            "master_id": mid,
            "title": master.title[:40],
            "published": summary.get("published", 0),
            "total": summary.get("total", 0),
            "stage": summary.get("stage", "unknown"),
            "errors": [e.get("type", "") for e in summary.get("errors", [])],
        })

    db.commit()

    return {
        "code": 0,
        "data": {
            "total": len(req.master_ids),
            "results": results,
        },
    }


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
async def run_pipeline(req: PipelineRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
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
    result = orchestrator.run_full_pipeline(master_data, platforms, db=db)

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
    result = ai_engine_mod.ai_engine.audit_product(req.title, req.desc, req.attrs)
    return {"code": 0, "data": result}


@app.post("/api/ai/gen_title", tags=["AI决策"])
async def ai_gen_title(req: AITitleRequest):
    """AI生成商品标题（返回3个版本）"""
    result = ai_engine_mod.ai_engine.generate_titles(req.product_info, req.platform)
    return {"code": 0, "data": result}


@app.post("/api/ai/optimize_desc", tags=["AI决策"])
async def ai_optimize_desc(req: AIDescRequest):
    """AI优化商品描述"""
    result = ai_engine_mod.ai_engine.optimize_description(req.title, req.desc, req.attrs)
    return {"code": 0, "data": result}


@app.post("/api/ai/keywords", tags=["AI决策"])
async def ai_extract_keywords(req: AIKeywordsRequest):
    """AI提取热搜关键词"""
    keywords = ai_engine_mod.ai_engine.extract_keywords(req.title, req.desc)
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
async def set_ai_key(req: AIKeyRequest, user: User = Depends(get_current_user)):
    """设置API Key"""
    return {"code": 0, "data": ai_config.set_api_key(req.api_key)}


@app.post("/api/ai/config/provider", tags=["AI配置"])
async def set_ai_provider(req: AIProviderRequest, user: User = Depends(get_current_user)):
    """切换AI提供商（openai/claude）"""
    return {"code": 0, "data": ai_config.set_provider(req.provider)}


@app.post("/api/ai/config/model", tags=["AI配置"])
async def set_ai_model(req: AIModelRequest, user: User = Depends(get_current_user)):
    """设置模型名称"""
    return {"code": 0, "data": ai_config.set_model(req.model)}


@app.post("/api/ai/config/test", tags=["AI配置"])
async def test_ai_connection(user: User = Depends(get_current_user)):
    """测试AI连接是否正常"""
    return {"code": 0, "data": ai_config.test_connection()}


# ============ AI图片处理 ============

class ImageProcessRequest(BaseModel):
    operations: List[str] = ["remove_bg", "watermark", "optimize"]
    watermark_text: str = ""
    platform: str = "taobao"


@app.post("/api/image/process", tags=["AI图片处理"])
async def process_image(user: User = Depends(get_current_user), 
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


# ============ 工作台仪表盘 ============

STATUS_LABELS = {0: "待处理", 1: "待审核", 2: "草稿", 3: "部分上架", 4: "全部上架", 5: "作废"}


@app.get("/api/dashboard/stats", tags=["工作台"])
async def dashboard_stats(db: Session = Depends(get_db)):
    """聚合统计数据"""
    total = db.query(ProductMaster).count()
    # 按状态分组
    from sqlalchemy import func
    status_rows = db.query(ProductMaster.status, func.count(ProductMaster.id)).group_by(ProductMaster.status).all()
    by_status = {STATUS_LABELS.get(s, f"未知{s}"): c for s, c in status_rows}
    # 按平台分组
    platform_rows = db.query(ProductPlatformRel.platform, func.count(ProductPlatformRel.id)).group_by(
        ProductPlatformRel.platform).all()
    by_platform = {p: c for p, c in platform_rows}
    # 最近流水线
    recent = orchestrator.list_tasks()[:5]
    # 待审核数
    pending = db.query(ProductMaster).filter(ProductMaster.status == 1).count()
    # 预警数(作废+待审核)
    alerts = db.query(ProductMaster).filter(ProductMaster.status.in_([1, 5])).count()

    return {
        "code": 0,
        "data": {
            "total": total,
            "published": by_status.get("全部上架", 0) + by_status.get("部分上架", 0),
            "pending": pending,
            "alerts": alerts,
            "by_status": by_status,
            "by_platform": by_platform,
            "recent_pipelines": recent,
        },
    }


# ============ 出口（审核发布） ============

@app.get("/api/audit/pending/list", tags=["审核"])
async def pending_audit(db: Session = Depends(get_db)):
    """待审核草稿列表"""
    rels = db.query(ProductPlatformRel).filter(
        ProductPlatformRel.platform_status == "pending_audit"
    ).all()
    return {"code": 0, "data": [{"id": r.id, "master_id": r.master_id, "platform": r.platform} for r in rels]}


@app.post("/api/audit/submit", tags=["审核"])
async def submit_audit(rel_id: int, approved: bool, comment: str = "", db: Session = Depends(get_db), user: User = Depends(get_current_user)):
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
async def publish_execute(req: PublishRequest, user: User = Depends(get_current_user)):
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

from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """v0.5.0+ 使用 lifespan 替代 on_event"""
    print("=" * 50)
    print("  全平台AI自动上架系统 v0.6.0")
    print("  六层架构 · AI驱动 · 全平台覆盖")
    print("=" * 50)
    try:
        init_db()
        print("[Startup] 数据库初始化完成")

        # 创建默认管理员账户
        from db.session import SessionLocal
        sess = SessionLocal()
        try:
            admin = sess.query(User).filter(User.username == "admin").first()
            if not admin:
                admin = User(
                    username="admin",
                    password_hash=hash_password("admin123"),
                    full_name="系统管理员",
                    role="admin",
                    is_active=1,
                )
                sess.add(admin)
                sess.commit()
                print("[Startup] 默认管理员已创建: admin / admin123")
        finally:
            sess.close()
    except Exception as e:
        print(f"[Startup] 数据库未连接(开发模式): {e}")
    print("[Startup] 系统就绪，访问 http://localhost:8800/docs 查看API文档")
    yield
    print("[Shutdown] 系统关闭")


# 将 lifespan 注入 app（必须在 app 创建后）
app.router.lifespan_context = lifespan


@app.get("/")
async def root():
    return {
        "name": "全平台AI自动上架系统",
        "version": "0.6.0",
        "status": "running",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8800, reload=True)

