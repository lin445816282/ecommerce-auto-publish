"""单元测试 — 数据模型 & 工具类"""
import sys
import os
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

def test_text_filter():
    from utils.text_filter import text_filter
    # 安全文本
    safe, _ = text_filter.check("这是一件优质纯棉T恤")
    assert safe, "正常文本不应被拦截"
    # 违禁文本
    safe, words = text_filter.check("高仿LV包包精仿品质")
    assert not safe, "违禁文本应被拦截"
    assert len(words) >= 2, f"应命中多个违禁词，实际: {words}"
    print("✅ text_filter 测试通过")

def test_retry_decorator():
    from utils.retry_utils import retry_with_backoff
    call_count = [0]

    @retry_with_backoff(max_retry=2)
    def flaky_func():
        call_count[0] += 1
        if call_count[0] < 3:
            raise Exception("临时错误")
        return "success"

    result = flaky_func()
    assert result == "success"
    assert call_count[0] == 3
    print("✅ retry_with_backoff 测试通过")

def test_product_model():
    from db.models import ProductMaster
    from datetime import datetime
    master = ProductMaster(
        inner_sku="TEST001",
        title="测试商品",
        price=99.0,
        cost_price=50.0,
        stock=100,
        source_type="manual",
    )
    assert master.inner_sku == "TEST001"
    # defaults from Column only apply at INSERT time, not __init__
    print("✅ ProductMaster 模型测试通过")

def test_adapter_base():
    from modules.adapter_layer.base_adapter import BasePlatformAdapter

    class MockAdapter(BasePlatformAdapter):
        def read_master_product(self, data):
            return data
        def translate_fields(self, data):
            return {"title": data.get("title", ""), "price": data.get("price", 0)}
        def check_required(self, payload):
            missing = []
            if not payload.get("title"):
                missing.append("title")
            return missing
        def upload_images(self, images):
            return [f"img_{i}" for i in range(len(images))]
        def submit_draft(self, payload):
            return "draft_001"
        def publish_draft(self, draft_id):
            return True

    adapter = MockAdapter({"shop_id": "test_shop"})
    result = adapter.full_pipeline({"title": "测试", "price": 99.0, "images": ["a.jpg"]})
    assert result["success"] is True
    assert result["draft_id"] == "draft_001"
    print("✅ BaseAdapter 测试通过")


if __name__ == "__main__":
    print("=" * 40)
    print("  单元测试")
    print("=" * 40)
    test_text_filter()
    test_retry_decorator()
    test_product_model()
    test_adapter_base()
    print("\n🎉 全部测试通过！")
