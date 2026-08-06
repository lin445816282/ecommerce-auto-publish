"""集成测试 — 完整流水线：抓取→合规闸→分发→适配→发布"""
import sys, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_crawl_and_text_filter():
    """测试1: 抓取1688 + 文字闸"""
    from modules.product_source.crawler import product_importer
    from utils.text_filter import text_filter

    # 正常商品
    url = "https://detail.1688.com/offer/123456789.html"
    result = product_importer.import_from_1688(url)
    assert result["success"], f"抓取应成功: {result}"
    data = result["data"]
    assert data["inner_sku"].startswith("1688-"), f"SKU格式错误: {data['inner_sku']}"

    # 文字闸检查
    text_result = text_filter.scan_product(data["title"], data["desc"])
    assert text_result["safe"], "正常商品不应被拦"

    print("✅ test_crawl_and_text_filter 通过")


def test_text_filter_blocks_banned_words():
    """测试2: 违禁词拦截"""
    from utils.text_filter import text_filter

    safe, words = text_filter.check("这是一件高仿LV精仿包包")
    assert not safe, "应被拦截"
    assert len(words) >= 2
    print("✅ test_text_filter_blocks_banned_words 通过")


def test_dispatcher_full_pipeline():
    """测试3: 调度器完整流水线"""
    from modules.scheduler_core.task_dispatcher import dispatcher

    # 正常商品
    master = {
        "id": 1,
        "inner_sku": "TEST001",
        "title": "优质纯棉T恤 舒适透气",
        "desc": "高品质面料，适合日常穿着",
        "price": 99.0,
        "cost_price": 50.0,
        "main_images": [],
        "attrs_json": {},
    }

    result = dispatcher.dispatch(master, ["taobao", "douyin"])
    assert result["passed"], f"正常商品应通过: {result}"
    assert result["stage"] == "dispatched"
    assert "taobao" in result["platform_results"]
    assert "douyin" in result["platform_results"]
    print("✅ test_dispatcher_full_pipeline 通过")


def test_dispatcher_blocks_banned_product():
    """测试4: 调度器拦截违禁商品"""
    from modules.scheduler_core.task_dispatcher import dispatcher

    master = {
        "id": 2,
        "inner_sku": "TEST002",
        "title": "高仿名牌包包精仿品质",
        "desc": "A货",
        "price": 500.0,
        "cost_price": 100.0,
        "main_images": [],
        "attrs_json": {},
    }

    result = dispatcher.dispatch(master, ["taobao"])
    assert not result["passed"], "违禁商品应被拦截"
    assert result["stage"] == "text_filter_blocked"
    assert result["status_code"] == 5  # 作废
    print("✅ test_dispatcher_blocks_banned_product 通过")


def test_price_anomaly_blocked():
    """测试5: 价格异常拦截"""
    from modules.scheduler_core.task_dispatcher import dispatcher

    master = {
        "id": 3,
        "inner_sku": "TEST003",
        "title": "正常商品标题",
        "desc": "正常描述",
        "price": 1.0,      # 售价1元
        "cost_price": 100.0,  # 成本100元，明显异常
        "main_images": [],
        "attrs_json": {},
    }

    result = dispatcher.dispatch(master, ["taobao"])
    assert not result["passed"], "价格异常应被拦截"
    assert result["stage"] == "price_check_blocked"
    print("✅ test_price_anomaly_blocked 通过")


def test_publish_gate_permission():
    """测试6: 发布权限控制"""
    from modules.export_gate.publisher import publish_gate, PublishPermission

    # 保存草稿
    draft_id = publish_gate.drafts.save_draft("taobao", 1, {"title": "test"})

    # 未审核不能发布
    can, reason = publish_gate.can_publish("admin", "taobao", draft_id)
    assert not can, "未审核不能发布"
    assert "未通过审核" in reason

    # 审核通过
    publish_gate.drafts.set_audit_status(draft_id, True)

    # admin可以发布
    can, reason = publish_gate.can_publish("admin", "taobao", draft_id)
    assert can, f"admin应有发布权限: {reason}"

    # operator没有发布权限
    can, reason = publish_gate.can_publish("operator", "taobao", draft_id)
    assert not can, "operator不应有发布权限"

    print("✅ test_publish_gate_permission 通过")


def test_adapter_pipeline():
    """测试7: 适配器完整流水线（淘宝+抖店）"""
    from modules.adapter_layer.taobao_adapter import TaobaoAdapter
    from modules.adapter_layer.douyin_adapter import DouyinAdapter

    master = {
        "inner_sku": "SKU001",
        "title": "测试商品",
        "desc": "测试描述",
        "price": 99.0,
        "stock": 100,
        "main_images": [],
        "detail_images": [],
        "attrs_json": {"品牌": "测试品牌"},
    }

    # 淘宝适配
    tb = TaobaoAdapter({"category_cid": "50010404"})
    tb_result = tb.full_pipeline(master)
    assert tb_result["success"], f"淘宝适配应成功: {tb_result}"
    assert tb_result["draft_id"] is not None

    # 抖店适配
    dy = DouyinAdapter({"category_id": "12345"})
    dy_result = dy.full_pipeline(master)
    assert dy_result["success"], f"抖店适配应成功: {dy_result}"
    assert dy_result["draft_id"] is not None

    print("✅ test_adapter_pipeline 通过")


def test_product_version_rollback():
    """测试8: 商品版本回滚"""
    from modules.product_master.manager import product_manager

    data_v1 = {"title": "标题V1", "price": 100, "inner_sku": "SKU001"}
    data_v2 = {"title": "标题V2", "price": 120, "inner_sku": "SKU001"}

    product_manager.save_version(1, data_v1)
    product_manager.save_version(1, data_v2)

    versions = product_manager.get_versions(1)
    assert len(versions) == 2

    # 回滚到V1
    rolled = product_manager.rollback(1, 1)
    assert rolled["title"] == "标题V1"
    assert rolled["price"] == 100

    print("✅ test_product_version_rollback 通过")


def test_status_transitions():
    """测试9: 状态流转合法性"""
    from modules.product_master.manager import product_manager

    # 草稿 → 待审核 ✅
    assert product_manager.can_transition(0, 1)
    # 草稿 → 已上架 ❌
    assert not product_manager.can_transition(0, 4)
    # 全部上架 → 作废 ✅
    assert product_manager.can_transition(4, 5)
    # 作废 → 草稿 ❌
    assert not product_manager.can_transition(5, 0)
    print("✅ test_status_transitions 通过")


if __name__ == "__main__":
    print("=" * 50)
    print("  集成测试 — 全平台AI自动上架系统")
    print("=" * 50)

    test_crawl_and_text_filter()
    test_text_filter_blocks_banned_words()
    test_dispatcher_full_pipeline()
    test_dispatcher_blocks_banned_product()
    test_price_anomaly_blocked()
    test_publish_gate_permission()
    test_adapter_pipeline()
    test_product_version_rollback()
    test_status_transitions()

    print("\n🎉 全部9个集成测试通过！")
