"""SQLAlchemy ORM 数据模型 — 商品主表 + 平台映射 + 任务调度 + 审核记录 + 平台配置"""
from sqlalchemy import Column, String, Text, Integer, Float, JSON, DateTime, ForeignKey, SmallInteger
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()


class ProductMaster(Base):
    """商品主表 — 全链路主键"""
    __tablename__ = "product_master"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="全局商品ID")
    inner_sku = Column(String(100), unique=True, nullable=False, comment="内部SKU编号")
    title = Column(String(500), default="", comment="通用标题")
    desc = Column(Text, default="", comment="通用详情")
    price = Column(Float, default=0.0, comment="售价")
    cost_price = Column(Float, default=0.0, comment="成本价")
    stock = Column(Integer, default=0, comment="库存")
    main_images = Column(JSON, default=list, comment="主图数组")
    detail_images = Column(JSON, default=list, comment="详情图数组")
    spec_json = Column(JSON, default=dict, comment="规格数据")
    attrs_json = Column(JSON, default=dict, comment="通用属性集合")
    source_type = Column(String(32), default="manual", comment="来源: 1688/manual/other")
    source_url = Column(String(1000), default="", comment="原始来源链接")
    version = Column(Integer, default=1, comment="数据版本号")
    status = Column(SmallInteger, default=0, comment="0草稿 1待审核 2已生成平台草稿 3部分上架 4全部上架 5作废")
    create_time = Column(DateTime, default=datetime.utcnow)
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    platforms = relationship("ProductPlatformRel", back_populates="master")


class ProductPlatformRel(Base):
    """平台商品映射表"""
    __tablename__ = "product_platform_rel"

    id = Column(Integer, primary_key=True, autoincrement=True)
    master_id = Column(Integer, ForeignKey("product_master.id"), nullable=False)
    platform = Column(String(32), nullable=False, comment="taobao/douyin/pdd/amazon")
    shop_id = Column(String(64), default="", comment="店铺ID")
    platform_item_id = Column(String(64), nullable=True, comment="平台返回商品ID")
    platform_draft_data = Column(JSON, default=dict, comment="适配后完整报文")
    platform_status = Column(String(32), default="draft", comment="draft/pending_audit/published/fail")
    error_msg = Column(Text, default="", comment="最近上传错误信息")
    create_time = Column(DateTime, default=datetime.utcnow)
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    master = relationship("ProductMaster", back_populates="platforms")


class TaskJob(Base):
    """任务调度表"""
    __tablename__ = "task_job"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_type = Column(String(32), nullable=False, comment="crawl/image_process/adapt/publish")
    master_id = Column(Integer, nullable=True, comment="商品ID，null为批量任务")
    platform = Column(String(32), default="", comment="目标平台")
    job_status = Column(SmallInteger, default=0, comment="0待执行 1执行中 2成功 3失败")
    retry_count = Column(Integer, default=0, comment="已重试次数")
    max_retry = Column(Integer, default=3, comment="最大重试次数")
    payload = Column(JSON, default=dict, comment="任务参数")
    result = Column(JSON, default=dict, comment="任务返回结果")
    create_time = Column(DateTime, default=datetime.utcnow)
    next_run_time = Column(DateTime, nullable=True, comment="断链续跑时间")


class AuditRecord(Base):
    """审核记录表"""
    __tablename__ = "audit_record"

    id = Column(Integer, primary_key=True, autoincrement=True)
    master_id = Column(Integer, nullable=False)
    platform = Column(String(32), default="")
    audit_type = Column(String(16), default="auto_ai", comment="auto_ai/manual")
    audit_result = Column(SmallInteger, default=0, comment="0待审核 1通过 2拒绝")
    audit_comment = Column(Text, default="", comment="拒绝原因")
    operator = Column(String(64), default="system")
    create_time = Column(DateTime, default=datetime.utcnow)


class PlatformConfig(Base):
    """平台配置表 — 类目映射/属性映射/店铺授权"""
    __tablename__ = "platform_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    platform = Column(String(32), nullable=False)
    shop_id = Column(String(64), default="")
    config_key = Column(String(64), nullable=False, comment="category_map/attr_map/api_auth")
    config_value = Column(JSON, default=dict)
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class User(Base):
    """用户表 — JWT认证"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    password_hash = Column(String(256), nullable=False)
    full_name = Column(String(128), default="")
    role = Column(String(16), default="operator", comment="admin/operator/viewer")
    is_active = Column(SmallInteger, default=1)
    last_login = Column(DateTime, nullable=True)
    create_time = Column(DateTime, default=datetime.utcnow)

print("[DB] Models defined: ProductMaster, ProductPlatformRel, TaskJob, AuditRecord, PlatformConfig, User")
