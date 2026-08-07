"""AI图片处理器 — 抠图 / 水印 / 平台优化"""
import io
import os
import base64
import hashlib
from typing import Dict, List, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

# === 平台图片规范 ===
PLATFORM_SPECS = {
    "taobao":  {"min_size": (800, 800),  "max_size": (1500, 1500), "max_count": 5,  "format": "JPEG", "quality": 90},
    "douyin":  {"min_size": (600, 600),  "max_size": (1200, 1200), "max_count": 9,  "format": "JPEG", "quality": 85},
    "pdd":     {"min_size": (480, 480),  "max_size": (1000, 1000), "max_count": 10, "format": "JPEG", "quality": 80},
    "amazon":  {"min_size": (1000, 1000), "max_size": (2000, 2000), "max_count": 9, "format": "JPEG", "quality": 95},
}

_here = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(_here, "..", "..", "data", "processed_images")


class ImageProcessor:
    """AI 图片处理引擎"""

    def __init__(self):
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        self._rembg_available = None  # lazy init

    def _try_rembg(self):
        if self._rembg_available is None:
            try:
                from rembg import remove
                remove.__name__  # force validation
                self._rembg_available = True
            except BaseException:
                self._rembg_available = False
        return self._rembg_available

    # ==================== 抠图 ====================

    def remove_background(self, image):
        """AI 智能抠图 → (RGBA图片, 方法名)"""
        if self._try_rembg():
            try:
                from rembg import remove
                result = remove(image)
                return result.convert("RGBA"), "rembg"
            except BaseException:
                self._rembg_available = False
        return self._pillow_remove_bg(image), "pillow_edge"

    def _pillow_remove_bg(self, image):
        """基于边缘检测的简易抠图"""
        img = image.convert("RGBA")
        gray = image.convert("L")
        edges = gray.filter(ImageFilter.FIND_EDGES)
        edges = edges.filter(ImageFilter.GaussianBlur(radius=3))
        mask = edges.point(lambda x: 255 if x > 25 else 120)
        result = Image.new("RGBA", img.size, (255, 255, 255, 0))
        result.paste(img, (0, 0), mask)
        return result

    # ==================== 水印 ====================

    def add_watermark(self, image, text="", position="bottom-right", opacity=0.3):
        """添加文字水印"""
        img = image.convert("RGBA")
        overlay = Image.new("RGBA", img.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(overlay)

        text = text or "AutoPublish"
        font_size = max(16, min(img.size) // 20)

        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except (OSError, IOError):
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        margin = 20

        pos_map = {
            "bottom-right": (img.size[0] - tw - margin, img.size[1] - th - margin),
            "bottom-left":  (margin, img.size[1] - th - margin),
            "top-right":    (img.size[0] - tw - margin, margin),
            "top-left":     (margin, margin),
            "center":       ((img.size[0] - tw) // 2, (img.size[1] - th) // 2),
        }
        pos = pos_map.get(position, pos_map["bottom-right"])

        alpha = int(255 * opacity)
        draw.text(pos, text, font=font, fill=(255, 255, 255, alpha))

        return Image.alpha_composite(img, overlay).convert("RGB")

    # ==================== 平台优化 ====================

    def optimize_for_platform(self, image, platform):
        """按平台规范裁剪/缩放/锐化"""
        spec = PLATFORM_SPECS.get(platform, PLATFORM_SPECS["taobao"])
        info = {"platform": platform, "actions": []}

        img = image.convert("RGB")
        w, h = img.size

        # 1. 正方形裁剪（取中心）
        if w != h:
            side = min(w, h)
            left = (w - side) // 2
            top = (h - side) // 2
            img = img.crop((left, top, left + side, top + side))
            info["actions"].append(f"crop_sq:{side}")

        # 2. 缩放到平台规范范围
        target_min = spec["min_size"][0]
        target_max = spec["max_size"][0]
        if img.size[0] < target_min:
            img = img.resize((target_min, target_min), Image.LANCZOS)
            info["actions"].append(f"upscale:{target_min}")
        elif img.size[0] > target_max:
            img = img.resize((target_max, target_max), Image.LANCZOS)
            info["actions"].append(f"downscale:{target_max}")

        # 3. 增强锐度
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(1.1)

        info["final_size"] = img.size
        info["format"] = spec["format"]
        info["quality"] = spec["quality"]
        return img, info

    # ==================== 完整处理管线 ====================

    def process_image(self, image_data, operations, watermark_text="", platform="taobao"):
        """完整处理: bytes → 抠图→水印→优化 → base64 + 文件"""
        results = {}

        try:
            img = Image.open(io.BytesIO(image_data))
            results["original_size"] = img.size
        except Exception as e:
            return {"ok": False, "error": f"图片加载失败: {e}"}

        # 1. 抠图
        if "remove_bg" in operations:
            img, method = self.remove_background(img)
            results["bg_removed"] = True
            results["bg_method"] = method

        # 2. 水印
        if "watermark" in operations:
            img = self.add_watermark(img, watermark_text)
            results["watermarked"] = True

        # 3. 平台优化
        if "optimize" in operations:
            img, opt_info = self.optimize_for_platform(img, platform)
            results["optimized"] = opt_info

        # 输出
        img_hash = hashlib.md5(image_data[:1024]).hexdigest()[:12]
        filename = f"{platform}_{img_hash}.png"
        filepath = os.path.join(OUTPUT_DIR, filename)
        img.save(filepath, "PNG", optimize=True)

        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        b64 = base64.b64encode(buf.getvalue()).decode()

        results["ok"] = True
        results["filepath"] = filepath
        results["filename"] = filename
        results["base64"] = b64
        results["final_size"] = img.size
        results["filesize_kb"] = round(os.path.getsize(filepath) / 1024, 1)
        return results

    def batch_process(self, images, operations, watermark_text="", platform="taobao"):
        """批量处理多张图片"""
        return [self.process_image(d, operations, watermark_text, platform) for d in images]


# 全局单例
image_processor = ImageProcessor()
# rembg checked lazily on first use
print("[ImageProcessor] Ready (rembg: lazy-init)")
