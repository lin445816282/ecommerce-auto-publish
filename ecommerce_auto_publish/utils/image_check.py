"""图片检测 — 第二道闸：水印检测、品牌Logo识别"""
import os


class ImageChecker:
    """图片闸：水印检测 + 品牌侵权检测"""

    # 已知品牌标志特征（后续可接入YOLO模型）
    BRAND_LOGOS = [
        "Nike", "Adidas", "Gucci", "LV", "Louis Vuitton",
        "Chanel", "Hermes", "Prada", "Dior", "Burberry",
        "Supreme", "Balenciaga", "Rolex", "Cartier",
    ]

    def __init__(self):
        self.watermark_model = None  # 后续加载AI模型

    def check_watermark(self, image_path: str) -> tuple:
        """
        水印检测（MVP阶段用简单规则，后续接入AI模型）
        返回: (has_watermark, confidence)
        """
        if not os.path.exists(image_path):
            return False, 0.0
        # TODO: 接入YOLOv8水印检测模型
        # MVP阶段返回False
        return False, 0.0

    def check_brand(self, image_path: str) -> tuple:
        """
        品牌Logo检测
        返回: (has_brand_logo, detected_brands)
        """
        if not os.path.exists(image_path):
            return False, []
        # TODO: 接入品牌Logo识别模型
        return False, []

    def full_check(self, image_list: list) -> dict:
        """完整图片检测"""
        result = {
            "all_clear": True,
            "watermark_images": [],
            "brand_images": [],
        }
        for img_path in image_list:
            has_wm, _ = self.check_watermark(img_path)
            if has_wm:
                result["all_clear"] = False
                result["watermark_images"].append(img_path)
            has_brand, brands = self.check_brand(img_path)
            if has_brand:
                result["all_clear"] = False
                result["brand_images"].append({"path": img_path, "brands": brands})
        return result


image_checker = ImageChecker()
print("[ImageChecker] Ready.")
