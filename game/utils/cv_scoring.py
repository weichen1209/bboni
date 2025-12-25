"""
OpenCV 形狀相似度評分模組
用於 Stage 2 薄膜沉積關卡的圓形繪製評分
以及 Stage 4 手繪電路關卡的形狀相似度評分
"""

import cv2
import numpy as np
from typing import List, Tuple, Optional
from enum import Enum


class ShapeType(Enum):
    """圖形類型枚舉"""
    PENTAGON_STAR = "pentagon_star"   # 五邊形+五角星
    CIRCLE_STAR = "circle_star"       # 圓形+五角星
    OVAL_RECT = "oval_rect"           # 橢圓+長方形
    PYRAMID = "pyramid"               # 金字塔


# 圖形元資料（用於 UI 顯示）
SHAPE_METADATA = {
    ShapeType.PENTAGON_STAR: {
        "name": "五角晶體",
        "display_name": "五角晶體",
        "description": "五邊形內含五角星",
        "difficulty": 2,
    },
    ShapeType.CIRCLE_STAR: {
        "name": "星環晶體",
        "display_name": "星環晶體",
        "description": "圓形內含五角星",
        "difficulty": 2,
    },
    ShapeType.OVAL_RECT: {
        "name": "矩晶結構",
        "display_name": "矩晶結構",
        "description": "橢圓形內含長方形",
        "difficulty": 1,
    },
    ShapeType.PYRAMID: {
        "name": "金字塔",
        "display_name": "金字塔晶體",
        "description": "立體金字塔形狀",
        "difficulty": 2,
    },
}


class CircleSimilarityScorer:
    """OpenCV 圓形相似度評分器"""

    def __init__(
        self,
        canvas_size: Tuple[int, int],
        target_center: Tuple[int, int],
        target_radius: int,
    ):
        """
        初始化評分器

        Args:
            canvas_size: 畫布大小 (width, height)
            target_center: 目標圓心 (x, y)
            target_radius: 目標圓半徑
        """
        self.canvas_size = canvas_size
        self.target_center = target_center
        self.target_radius = target_radius
        self._target_contour = self._create_target_contour(filled=False)
        self._target_contour_filled = self._create_target_contour(filled=True)

    def _create_target_contour(self, filled: bool = False) -> np.ndarray:
        """建立目標圓的輪廓用於比較"""
        img = np.zeros((self.canvas_size[1], self.canvas_size[0]), dtype=np.uint8)
        thickness = -1 if filled else 2
        cv2.circle(img, self.target_center, self.target_radius, 255, thickness)
        contours, _ = cv2.findContours(img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        return contours[0] if contours else np.array([])

    def _points_to_binary_image(
        self, points: List[Tuple[int, int]], line_width: int = 6, filled: bool = False
    ) -> np.ndarray:
        """將軌跡點渲染為二值圖像"""
        img = np.zeros((self.canvas_size[1], self.canvas_size[0]), dtype=np.uint8)
        if len(points) < 2:
            return img
        pts = np.array(points, dtype=np.int32)
        if filled:
            # 封閉並填充多邊形
            cv2.fillPoly(img, [pts], 255)
        else:
            cv2.polylines(img, [pts], isClosed=False, color=255, thickness=line_width)
        return img

    def calculate_hu_moment_score(self, points: List[Tuple[int, int]]) -> float:
        """
        使用 Hu Moments (cv2.matchShapes) 計算形狀相似度
        使用填充形狀進行比較以獲得準確結果

        Returns:
            0-100 分數 (越高越相似)
        """
        if len(points) < 10:
            return 0.0

        # 使用填充形狀進行比較
        drawn_img = self._points_to_binary_image(points, filled=True)
        contours, _ = cv2.findContours(
            drawn_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE
        )

        if not contours or len(self._target_contour_filled) == 0:
            return 0.0

        # 使用最大輪廓
        drawn_contour = max(contours, key=cv2.contourArea)

        # matchShapes: 0 = 完全相同，越大越不同
        match_value = cv2.matchShapes(
            self._target_contour_filled, drawn_contour, cv2.CONTOURS_MATCH_I1, 0
        )

        # 轉換為 0-100 分數 (指數衰減，調整係數以獲得合理範圍)
        score = 100 * np.exp(-match_value * 10)
        return float(np.clip(score, 0, 100))

    def calculate_circularity_cv(self, points: List[Tuple[int, int]]) -> float:
        """
        使用 OpenCV 計算圓度: 4*pi*area / perimeter^2
        完美圓形 = 1.0
        使用填充形狀以獲得準確的面積計算

        Returns:
            0-100 分數
        """
        if len(points) < 10:
            return 0.0

        # 使用填充形狀計算圓度
        drawn_img = self._points_to_binary_image(points, filled=True)
        contours, _ = cv2.findContours(
            drawn_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE
        )

        if not contours:
            return 0.0

        contour = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(contour)
        perimeter = cv2.arcLength(contour, True)

        if perimeter == 0:
            return 0.0

        circularity = 4 * np.pi * area / (perimeter**2)
        return float(np.clip(circularity * 100, 0, 100))

    def calculate_center_distance_score(self, points: List[Tuple[int, int]]) -> float:
        """
        計算繪製形狀中心與目標圓心的距離評分

        Returns:
            0-100 分數
        """
        if len(points) < 3:
            return 0.0

        drawn_img = self._points_to_binary_image(points)
        contours, _ = cv2.findContours(
            drawn_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE
        )

        if not contours:
            return 0.0

        contour = max(contours, key=cv2.contourArea)
        M = cv2.moments(contour)

        if M["m00"] == 0:
            return 0.0

        cx = int(M["m10"] / M["m00"])
        cy = int(M["m01"] / M["m00"])

        distance = np.sqrt(
            (cx - self.target_center[0]) ** 2 + (cy - self.target_center[1]) ** 2
        )
        max_distance = self.target_radius  # 以半徑為最大容許距離

        score = 100 * (1 - min(distance / max_distance, 1.0))
        return float(score)

    def calculate_radius_match_score(self, points: List[Tuple[int, int]]) -> float:
        """
        計算繪製圓半徑與目標半徑的匹配度

        Returns:
            0-100 分數
        """
        if len(points) < 3:
            return 0.0

        drawn_img = self._points_to_binary_image(points)
        contours, _ = cv2.findContours(
            drawn_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE
        )

        if not contours:
            return 0.0

        contour = max(contours, key=cv2.contourArea)

        # 擬合最小包圍圓
        (x, y), radius = cv2.minEnclosingCircle(contour)

        # 比較半徑
        radius_error = abs(radius - self.target_radius) / self.target_radius
        score = 100 * (1 - min(radius_error, 1.0))
        return float(score)

    def calculate_fourier_descriptor_score(
        self, points: List[Tuple[int, int]], num_descriptors: int = 10
    ) -> float:
        """
        使用傅立葉描述子計算形狀平滑度和相似度
        評估繪製軌跡的圓形特徵

        Returns:
            0-100 分數
        """
        if len(points) < 10:
            return 0.0

        pts_array = np.array(points)
        drawn_fd = self._compute_fourier_descriptors(pts_array, num_descriptors)

        if drawn_fd is None:
            return 0.0

        # 對於理想圓形，傅立葉描述子應該集中在低頻成分
        # 計算能量集中度：前幾個描述子的能量佔總能量的比例
        total_energy = np.sum(drawn_fd**2) + 1e-6
        low_freq_energy = np.sum(drawn_fd[:3] ** 2)
        concentration = low_freq_energy / total_energy

        # 高集中度表示形狀平滑且接近圓形
        score = float(np.clip(concentration * 100, 0, 100))
        return score

    def _compute_fourier_descriptors(
        self, points: np.ndarray, num_descriptors: int
    ) -> Optional[np.ndarray]:
        """計算輪廓的正規化傅立葉描述子"""
        if len(points) < 4:
            return None

        # 轉換為複數
        complex_points = points[:, 0] + 1j * points[:, 1]

        # FFT
        fourier = np.fft.fft(complex_points)

        # 平移不變性
        fourier[0] = 0

        # 尺度不變性
        if np.abs(fourier[1]) > 0:
            fourier = fourier / np.abs(fourier[1])

        # 取前 N 個描述子 (透過取絕對值達成旋轉不變性)
        descriptors = np.abs(fourier[1 : num_descriptors + 1])
        return descriptors

    def get_combined_score(
        self, points: List[Tuple[int, int]], weights: dict = None
    ) -> Tuple[int, dict]:
        """
        計算加權組合的總分數

        Args:
            points: 軌跡點列表 [(x, y), ...]
            weights: 可選的權重覆蓋

        Returns:
            (總分數, 各項分數字典)
        """
        default_weights = {
            "hu_moment": 0.30,
            "circularity": 0.20,
            "center_distance": 0.20,
            "radius_match": 0.15,
            "fourier": 0.15,
        }

        if weights:
            default_weights.update(weights)

        # 計算各項分數
        scores = {
            "hu_moment": self.calculate_hu_moment_score(points),
            "circularity": self.calculate_circularity_cv(points),
            "center_distance": self.calculate_center_distance_score(points),
            "radius_match": self.calculate_radius_match_score(points),
            "fourier": self.calculate_fourier_descriptor_score(points),
        }

        # 加權組合
        total = sum(scores[k] * default_weights[k] for k in scores)

        return int(total), scores


class ShapeSimilarityScorer:
    """通用形狀相似度評分器 - 用於 Stage 4 手繪電路"""

    def __init__(self, canvas_size: Tuple[int, int]):
        """
        初始化評分器

        Args:
            canvas_size: 畫布大小 (width, height)
        """
        self.canvas_size = canvas_size
        self._target_image: Optional[np.ndarray] = None

    def create_target_h_image(self, thickness: int = 12) -> np.ndarray:
        """
        建立 H 形目標圖像

        Args:
            thickness: 線條粗細

        Returns:
            H 形二值圖像
        """
        w, h = self.canvas_size
        img = np.zeros((h, w), dtype=np.uint8)

        # H 的尺寸比例
        margin = min(w, h) // 6
        h_width = w - 2 * margin
        h_height = h - 2 * margin

        # 左側垂直線
        left_x = margin
        cv2.line(img, (left_x, margin), (left_x, h - margin), 255, thickness)

        # 右側垂直線
        right_x = w - margin
        cv2.line(img, (right_x, margin), (right_x, h - margin), 255, thickness)

        # 中間水平線
        mid_y = h // 2
        cv2.line(img, (left_x, mid_y), (right_x, mid_y), 255, thickness)

        self._target_image = img
        return img

    def create_target_pentagon_star_image(self, thickness: int = 12) -> np.ndarray:
        """
        建立五角晶體目標圖像（五邊形 + 內部五角星）

        Args:
            thickness: 線條粗細

        Returns:
            五角晶體形狀二值圖像
        """
        import math
        w, h = self.canvas_size
        img = np.zeros((h, w), dtype=np.uint8)

        center_x, center_y = w // 2, h // 2
        radius = int(min(w, h) * 0.4)

        # 計算五邊形頂點 (從頂部開始，順時針)
        pentagon_points = []
        for i in range(5):
            angle = math.radians(-90 + i * 72)  # 從頂部開始
            x = int(center_x + radius * math.cos(angle))
            y = int(center_y + radius * math.sin(angle))
            pentagon_points.append((x, y))

        # 繪製五邊形外框
        pts = np.array(pentagon_points, dtype=np.int32)
        cv2.polylines(img, [pts], isClosed=True, color=255, thickness=thickness)

        # 繪製內部五角星 (連接每隔一個頂點)
        for i in range(5):
            start = pentagon_points[i]
            end = pentagon_points[(i + 2) % 5]
            cv2.line(img, start, end, 255, thickness)

        self._target_image = img
        return img

    def create_target_circle_star_image(self, thickness: int = 12) -> np.ndarray:
        """
        建立星環晶體目標圖像（圓形 + 內部五角星）

        Args:
            thickness: 線條粗細

        Returns:
            星環晶體形狀二值圖像
        """
        import math
        w, h = self.canvas_size
        img = np.zeros((h, w), dtype=np.uint8)

        center_x, center_y = w // 2, h // 2
        radius = int(min(w, h) * 0.4)

        # 繪製圓形外框
        cv2.circle(img, (center_x, center_y), radius, 255, thickness)

        # 計算五角星頂點 (內切於圓)
        star_points = []
        for i in range(5):
            angle = math.radians(-90 + i * 72)  # 從頂部開始
            x = int(center_x + radius * 0.9 * math.cos(angle))
            y = int(center_y + radius * 0.9 * math.sin(angle))
            star_points.append((x, y))

        # 繪製五角星 (連接每隔一個頂點)
        for i in range(5):
            start = star_points[i]
            end = star_points[(i + 2) % 5]
            cv2.line(img, start, end, 255, thickness)

        self._target_image = img
        return img

    def create_target_oval_rect_image(self, thickness: int = 12) -> np.ndarray:
        """
        建立矩晶結構目標圖像（橢圓形 + 內部長方形）

        Args:
            thickness: 線條粗細

        Returns:
            矩晶結構形狀二值圖像
        """
        w, h = self.canvas_size
        img = np.zeros((h, w), dtype=np.uint8)

        center_x, center_y = w // 2, h // 2

        # 橢圓尺寸
        oval_a = int(w * 0.4)  # 橫軸半徑
        oval_b = int(h * 0.35)  # 縱軸半徑

        # 繪製橢圓形外框
        cv2.ellipse(img, (center_x, center_y), (oval_a, oval_b), 0, 0, 360, 255, thickness)

        # 內部長方形尺寸 (稍微內縮)
        rect_w = int(oval_a * 1.2)
        rect_h = int(oval_b * 1.0)

        # 繪製內部長方形
        rect_left = center_x - rect_w // 2
        rect_top = center_y - rect_h // 2
        rect_right = center_x + rect_w // 2
        rect_bottom = center_y + rect_h // 2
        cv2.rectangle(img, (rect_left, rect_top), (rect_right, rect_bottom), 255, thickness)

        self._target_image = img
        return img

    def create_target_pyramid_image(self, thickness: int = 12) -> np.ndarray:
        """
        建立金字塔晶體目標圖像（3D 四角錐）

        Args:
            thickness: 線條粗細

        Returns:
            金字塔晶體形狀二值圖像
        """
        w, h = self.canvas_size
        img = np.zeros((h, w), dtype=np.uint8)

        center_x, center_y = w // 2, h // 2

        # 金字塔尺寸
        base_w = int(w * 0.6)
        base_h = int(h * 0.3)
        apex_offset_y = int(h * 0.35)  # 頂點向上偏移

        # 底部菱形的四個角 (透視效果)
        bottom_center_y = center_y + int(h * 0.15)
        left_point = (center_x - base_w // 2, bottom_center_y)
        right_point = (center_x + base_w // 2, bottom_center_y)
        front_point = (center_x, bottom_center_y + base_h // 2)
        back_point = (center_x, bottom_center_y - base_h // 2)

        # 頂點
        apex = (center_x, center_y - apex_offset_y)

        # 繪製底部菱形
        cv2.line(img, left_point, front_point, 255, thickness)
        cv2.line(img, front_point, right_point, 255, thickness)
        cv2.line(img, right_point, back_point, 255, thickness)
        cv2.line(img, back_point, left_point, 255, thickness)

        # 繪製從頂點到底部四角的邊
        cv2.line(img, apex, left_point, 255, thickness)
        cv2.line(img, apex, right_point, 255, thickness)
        cv2.line(img, apex, front_point, 255, thickness)
        cv2.line(img, apex, back_point, 255, thickness)

        self._target_image = img
        return img

    def create_target_image(self, shape_type: ShapeType, thickness: int = 12) -> np.ndarray:
        """
        根據圖形類型建立目標圖像（統一介面）

        Args:
            shape_type: 圖形類型枚舉
            thickness: 線條粗細

        Returns:
            目標形狀二值圖像
        """
        if shape_type == ShapeType.PENTAGON_STAR:
            return self.create_target_pentagon_star_image(thickness)
        elif shape_type == ShapeType.CIRCLE_STAR:
            return self.create_target_circle_star_image(thickness)
        elif shape_type == ShapeType.OVAL_RECT:
            return self.create_target_oval_rect_image(thickness)
        elif shape_type == ShapeType.PYRAMID:
            return self.create_target_pyramid_image(thickness)
        else:
            # 預設返回五角晶體
            return self.create_target_pentagon_star_image(thickness)

    def get_thumbnail(
        self, shape_type: ShapeType, size: Tuple[int, int] = (160, 120)
    ) -> np.ndarray:
        """
        生成指定圖形的縮圖（用於選擇界面）

        Args:
            shape_type: 圖形類型枚舉
            size: 縮圖尺寸 (width, height)

        Returns:
            縮圖二值圖像
        """
        # 暫存原始畫布大小
        original_size = self.canvas_size
        original_target = self._target_image

        # 使用縮圖尺寸創建圖形
        self.canvas_size = size
        thumbnail = self.create_target_image(shape_type, thickness=4)

        # 恢復原始設定
        self.canvas_size = original_size
        self._target_image = original_target

        return thumbnail

    def points_to_image(
        self, points: List[Tuple[int, int]], thickness: int = 8
    ) -> np.ndarray:
        """
        將軌跡點轉換為二值圖像

        Args:
            points: 軌跡點列表
            thickness: 線條粗細

        Returns:
            二值圖像
        """
        w, h = self.canvas_size
        img = np.zeros((h, w), dtype=np.uint8)

        if len(points) < 2:
            return img

        pts = np.array(points, dtype=np.int32)
        cv2.polylines(img, [pts], isClosed=False, color=255, thickness=thickness)

        return img

    def calculate_iou(self, drawn_img: np.ndarray, target_img: np.ndarray) -> float:
        """
        計算 IoU (Intersection over Union)

        Args:
            drawn_img: 繪製的二值圖像
            target_img: 目標二值圖像

        Returns:
            0-100 分數
        """
        # 膨脹目標區域以增加容許度
        kernel = np.ones((5, 5), np.uint8)
        target_dilated = cv2.dilate(target_img, kernel, iterations=2)

        intersection = np.logical_and(drawn_img > 0, target_dilated > 0).sum()
        union = np.logical_or(drawn_img > 0, target_dilated > 0).sum()

        if union == 0:
            return 0.0

        iou = intersection / union
        return float(iou * 100)

    def calculate_coverage(
        self, drawn_img: np.ndarray, target_img: np.ndarray
    ) -> float:
        """
        計算目標被覆蓋的比例

        Args:
            drawn_img: 繪製的二值圖像
            target_img: 目標二值圖像

        Returns:
            0-100 分數
        """
        # 膨脹繪製區域
        kernel = np.ones((5, 5), np.uint8)
        drawn_dilated = cv2.dilate(drawn_img, kernel, iterations=1)

        target_pixels = (target_img > 0).sum()
        if target_pixels == 0:
            return 0.0

        covered = np.logical_and(drawn_dilated > 0, target_img > 0).sum()
        coverage = covered / target_pixels

        return float(min(coverage, 1.0) * 100)

    def calculate_precision(
        self, drawn_img: np.ndarray, target_img: np.ndarray
    ) -> float:
        """
        計算繪製準確度（繪製在目標範圍內的比例）

        Args:
            drawn_img: 繪製的二值圖像
            target_img: 目標二值圖像

        Returns:
            0-100 分數
        """
        # 膨脹目標區域以增加容許度
        kernel = np.ones((7, 7), np.uint8)
        target_dilated = cv2.dilate(target_img, kernel, iterations=3)

        drawn_pixels = (drawn_img > 0).sum()
        if drawn_pixels == 0:
            return 0.0

        on_target = np.logical_and(drawn_img > 0, target_dilated > 0).sum()
        precision = on_target / drawn_pixels

        return float(precision * 100)

    def get_combined_score(
        self, drawn_points: List[Tuple[int, int]], weights: dict = None
    ) -> Tuple[int, dict]:
        """
        計算綜合評分

        Args:
            drawn_points: 繪製的軌跡點
            weights: 可選的權重覆蓋

        Returns:
            (總分數, 各項分數字典)
        """
        default_weights = {
            "coverage": 0.35,
            "precision": 0.35,
            "iou": 0.30,
        }

        if weights:
            default_weights.update(weights)

        # 確保目標圖像存在
        if self._target_image is None:
            self.create_target_h_image()

        # 轉換軌跡為圖像
        drawn_img = self.points_to_image(drawn_points)

        # 計算各項分數
        scores = {
            "coverage": self.calculate_coverage(drawn_img, self._target_image),
            "precision": self.calculate_precision(drawn_img, self._target_image),
            "iou": self.calculate_iou(drawn_img, self._target_image),
        }

        # 加權組合
        total = sum(scores[k] * default_weights[k] for k in scores)

        return int(total), scores

    def get_target_overlay_image(
        self, alpha: float = 0.3, color: Tuple[int, int, int] = (0, 255, 0)
    ) -> np.ndarray:
        """
        取得目標圖形的彩色疊加圖像 (用於顯示)

        Args:
            alpha: 透明度
            color: BGR 顏色

        Returns:
            BGRA 格式的疊加圖像
        """
        if self._target_image is None:
            self.create_target_h_image()

        w, h = self.canvas_size
        overlay = np.zeros((h, w, 4), dtype=np.uint8)

        # 將目標區域填充顏色
        mask = self._target_image > 0
        overlay[mask, 0] = color[0]  # B
        overlay[mask, 1] = color[1]  # G
        overlay[mask, 2] = color[2]  # R
        overlay[mask, 3] = int(255 * alpha)  # A

        return overlay
