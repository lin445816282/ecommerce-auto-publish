"""文字违规检测 — 第一道闸：违禁词过滤"""
import os
import re
from config.settings import BAN_WORD_FILE

# 默认违禁词表（可外部扩展ban_word.txt）
DEFAULT_BAN_WORDS = [
    "仿牌", "高仿", "精仿", "A货", "原单", "尾单",
    "走私", "水货", "盗版", "翻版", "假冒",
    "迷药", "枪支", "弹药", "毒品", "管制刀具",
    "色情", "赌博", "传销", "诈骗",
]


class TextFilter:
    """文字闸"""

    def __init__(self, word_file: str = None):
        self.words = list(DEFAULT_BAN_WORDS)
        if word_file and os.path.exists(word_file):
            with open(word_file, "r", encoding="utf-8") as f:
                extra = [w.strip() for w in f if w.strip()]
                self.words.extend(extra)
        self.pattern = re.compile("|".join(re.escape(w) for w in self.words), re.IGNORECASE)

    def check(self, text: str) -> tuple:
        """
        检查文本是否包含违禁词
        返回: (is_safe, matched_words)
        """
        if not text:
            return True, []
        matches = self.pattern.findall(text)
        return len(matches) == 0, matches

    def scan_product(self, title: str, desc: str, attrs: dict = None) -> dict:
        """扫描商品全部文本字段"""
        result = {"safe": True, "hits": {}}
        for field_name, text in [("title", title), ("desc", desc)]:
            safe, words = self.check(text or "")
            if not safe:
                result["safe"] = False
                result["hits"][field_name] = words
        if attrs:
            for k, v in attrs.items():
                safe, words = self.check(str(v))
                if not safe:
                    result["safe"] = False
                    result["hits"][f"attrs.{k}"] = words
        return result


# 全局单例
text_filter = TextFilter()

print(f"[TextFilter] Loaded {len(text_filter.words)} ban words.")
