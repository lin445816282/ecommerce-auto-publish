"""AI配置管理器 — 运行时配置，无需重启"""
import json
import os
from typing import Dict, Optional

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "ai_config.json")


class AIConfigManager:
    """AI配置持久化：API Key + Provider + Model"""

    def __init__(self):
        self._config = self._load()

    def _load(self) -> Dict:
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "provider": "openai",
            "api_key": "",
            "model": "gpt-4",
            "enabled": False,
            # Claude settings
            "claude_model": "claude-3-5-sonnet-20241022",
            # OpenAI settings
            "openai_model": "gpt-4",
            "temperature": 0.7,
            "max_tokens": 2048,
        }

    def _save(self):
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self._config, f, indent=2, ensure_ascii=False)

    def get_config(self) -> Dict:
        """获取当前配置（隐藏API Key中间部分）"""
        cfg = dict(self._config)
        key = cfg.get("api_key", "")
        if key and len(key) > 8:
            cfg["api_key_masked"] = key[:4] + "*" * (len(key) - 8) + key[-4:]
        else:
            cfg["api_key_masked"] = "未设置" if not key else key
        return cfg

    def set_api_key(self, key: str) -> Dict:
        self._config["api_key"] = key.strip()
        self._config["enabled"] = bool(key.strip())
        self._save()
        # 通知 engine 更新
        self._reload_engine()
        return {"ok": True, "msg": "API Key已保存", "enabled": self._config["enabled"]}

    def set_provider(self, provider: str) -> Dict:
        valid = ["openai", "claude"]
        if provider not in valid:
            return {"ok": False, "msg": f"无效提供商，可选: {valid}"}
        self._config["provider"] = provider
        # Auto-select model based on provider
        if provider == "claude":
            self._config["model"] = self._config["claude_model"]
        else:
            self._config["model"] = self._config["openai_model"]
        self._save()
        self._reload_engine()
        return {"ok": True, "msg": f"已切换到 {provider.upper()}", "provider": provider, "model": self._config["model"]}

    def set_model(self, model: str) -> Dict:
        self._config["model"] = model.strip()
        self._save()
        self._reload_engine()
        return {"ok": True, "msg": f"模型已设为 {model}"}

    def test_connection(self) -> Dict:
        """测试AI连接"""
        if not self._config.get("api_key"):
            return {"ok": False, "msg": "请先设置API Key"}
        try:
            from .engine import AIEngine
            test_engine = AIEngine(
                api_key=self._config["api_key"],
                model=self._config["model"]
            )
            # 发送一个简单请求测试连通性
            result = test_engine.generate_titles({"title": "测试商品"}, "通用")
            return {"ok": True, "msg": "连接成功!", "sample": result}
        except Exception as e:
            return {"ok": False, "msg": f"连接失败: {str(e)}"}

    def _reload_engine(self):
        """热更新全局AI引擎"""
        try:
            from . import engine as eng_module
            provider = self._config.get("provider", "openai")
            key = self._config.get("api_key", "")
            model = self._config.get("model", "gpt-4")
            os.environ["AI_PROVIDER"] = provider
            os.environ["AI_API_KEY"] = key
            os.environ["AI_MODEL"] = model
            eng_module.ai_engine = eng_module.AIEngine(
                api_key=key, model=model
            )
            print(f"[AIConfig] Engine reloaded: {provider}/{model}")
        except Exception as e:
            print(f"[AIConfig] Engine reload failed: {e}")


ai_config = AIConfigManager()
print(f"[AIConfig] Manager ready. Provider: {ai_config._config['provider']}, Enabled: {ai_config._config['enabled']}")
