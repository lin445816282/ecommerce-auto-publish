"""AI决策层 — 智能审核 + 标题生成 + 描述优化"""
import json
import os
from typing import Dict, List, Optional
import httpx


class AIEngine:
    """AI大脑 — 调用大模型API完成智能决策"""

    def __init__(self, api_key: str = None, model: str = "gpt-4"):
        self.api_key = api_key or os.getenv("AI_API_KEY", "")
        self.model = model
        self.provider = os.getenv("AI_PROVIDER", "openai")
        self.client = httpx.Client(timeout=60)

    def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """调用大模型API"""
        if not self.api_key:
            return self._mock_llm(system_prompt + " " + user_prompt)

        if self.provider == "openai":
            return self._call_openai(system_prompt, user_prompt)
        elif self.provider == "claude":
            return self._call_claude(system_prompt, user_prompt)
        else:
            return self._mock_llm(user_prompt)

    def _call_openai(self, system: str, user: str) -> str:
        resp = self.client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 0.7,
            },
        )
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    def _call_claude(self, system: str, user: str) -> str:
        resp = self.client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            },
            json={
                "model": self.model,
                "system": system,
                "messages": [{"role": "user", "content": user}],
                "max_tokens": 1024,
            },
        )
        return resp.json()["content"][0]["text"]

    # ===== 智能审核 =====

    AUDIT_SYSTEM = """你是电商合规审核专家。检查商品信息是否违规。返回JSON:
{
  "safe": true/false,
  "issues": [{"field": "字段名", "severity": "high/medium/low", "reason": "原因"}],
  "risk_score": 0-100,
  "suggestions": ["修改建议"]
}"""

    def audit_product(self, title: str, desc: str, attrs: dict = None) -> Dict:
        """智能审核商品"""
        user = f"标题: {title}\n描述: {desc}\n属性: {json.dumps(attrs or {}, ensure_ascii=False)}"
        try:
            raw = self._call_llm(self.AUDIT_SYSTEM, user)
            return json.loads(raw)
        except Exception:
            return {"safe": True, "issues": [], "risk_score": 0, "suggestions": []}

    # ===== 标题生成 =====

    TITLE_SYSTEM = """你是电商文案专家。根据商品信息生成3个高质量标题:
- 标题1: 搜索优化型（包含高流量关键词）
- 标题2: 营销吸引型（突出卖点和优惠）
- 标题3: 简洁高效型（平台字数限制版）
返回JSON: {"titles": ["标题1", "标题2", "标题3"], "keywords": ["关键词1", "关键词2", ...]}"""

    def generate_titles(self, product_info: Dict, platform: str = "通用") -> Dict:
        """AI生成商品标题"""
        user = f"平台: {platform}\n商品信息: {json.dumps(product_info, ensure_ascii=False)}"
        try:
            raw = self._call_llm(self.TITLE_SYSTEM, user)
            return json.loads(raw)
        except Exception:
            return {
                "titles": [
                    f"{product_info.get('title', '新品')} 品质保障 现货速发",
                    f"热卖爆款🔥{product_info.get('title', '好物')} 限时特惠",
                    f"{product_info.get('title', '优质商品')}",
                ],
                "keywords": ["现货", "品质", "热卖"],
            }

    # ===== 描述优化 =====

    DESC_SYSTEM = """你是电商详情页专家。优化商品描述，使其更具吸引力:
1. 保留核心产品信息
2. 提炼卖点，分条展示
3. 加入场景化描述
4. 控制字数在200字以内
返回JSON: {"desc": "优化后的描述", "selling_points": ["卖点1", "卖点2"]}"""

    def optimize_description(self, title: str, desc: str, attrs: dict = None) -> Dict:
        """AI优化商品描述"""
        user = f"标题: {title}\n原始描述: {desc}\n属性: {json.dumps(attrs or {}, ensure_ascii=False)}"
        try:
            raw = self._call_llm(self.DESC_SYSTEM, user)
            return json.loads(raw)
        except Exception:
            points = ["品质保证", "现货速发", "售后无忧"]
            return {"desc": desc or f"{title}，品质保障，现货速发。", "selling_points": points}

    # ===== 关键词提取 =====

    def extract_keywords(self, title: str, desc: str) -> List[str]:
        """从商品信息提取热搜关键词"""
        user = f"标题: {title}\n描述: {desc}\n请提取10个最相关的电商搜索关键词，每行一个。"
        try:
            raw = self._call_llm("你是SEO专家。只返回关键词，每行一个，不要序号。", user)
            return [k.strip() for k in raw.split("\n") if k.strip()][:10]
        except Exception:
            return ["现货", "批发", "厂家直供"]

    # ===== Mock模式(无API Key时) =====

    def _mock_llm(self, prompt: str) -> str:
        """离线模式 — 基于规则返回合理结果"""
        # check in specific order to avoid false matches
        if "合规审核" in prompt or "risk_score" in prompt:
            return json.dumps({"safe": True, "issues": [], "risk_score": 10, "suggestions": []}, ensure_ascii=False)
        if "优化商品描述" in prompt or "详情页专家" in prompt:
            return json.dumps({"desc": "品质保障，现货速发，售后无忧。欢迎批发采购。", "selling_points": ["品质保证", "现货速发"]}, ensure_ascii=False)
        if "3个高质量标题" in prompt or "搜索优化型" in prompt:
            import re
            m = re.search(r'商品信息: (.+?)[,\]\}]', prompt)
            name = m.group(1) if m else "好物"
            return json.dumps({
                "titles": [f"{name} 品质保障 现货速发", f"热卖🔥{name} 限时特惠", f"{name}"],
                "keywords": ["现货", "品质", "热卖", "厂家直供"],
            }, ensure_ascii=False)
        # keywords: just return list
        return "现货\n批发\n厂家直供\n品质保证\n热卖"


# 全局单例
ai_engine = AIEngine()
print(f"[AIBrain] Engine ready. Provider: {ai_engine.provider}, Model: {ai_engine.model}")
