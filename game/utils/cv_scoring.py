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
    TRANSISTOR = "transistor"
    CAPACITOR = "capacitor"
    IC_CHIP = "ic"
    OP_AMP = "opamp"


# 圖形元資料（用於 UI 顯示）
SHAPE_METADATA = {
    ShapeType.TRANSISTOR: {
        "name": "電晶體",
        "display_name": "NPN 電晶體",
        "description": "BJT 三極管符號",
        "difficulty": 3,
    },
    ShapeType.CAPACITOR: {
        "name": "變壓器",
        "display_name": "變壓器",
        "description": "兩組線圈符號",
        "difficulty": 3,
    },
    ShapeType.IC_CHIP: {
        "name": "積體電路",
        "display_name": "IC 晶片",
        "description": "晶片封裝圖案",
        "difficulty": 3,
    },
    ShapeType.OP_AMP: {
        "name": "比較器",
        "display_name": "比較器電路",
        "description": "Comparator 電路符號（含 V+/V- 電源腳位）",
        "difficulty": 3,
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

    def create_target_transistor_image(self, thickness: int = 12) -> np.ndarray:
        """
        建立 NPN 電晶體 (BJT) 目標圖像
        圓形 + 基極線 + 集電極/發射極（帶箭頭）

        Args:
            thickness: 線條粗細

        Returns:
            NPN 電晶體形狀二值圖像
        """
        w, h = self.canvas_size
        img = np.zeros((h, w), dtype=np.uint8)

        center_x, center_y = w // 2, h // 2
        radius = min(w, h) // 4

        # 繪製圓形外框
        cv2.circle(img, (center_x, center_y), radius, 255, thickness)

        # 基極線（左側水平線進入圓）
        base_x = center_x - radius
        cv2.line(img, (base_x - radius, center_y), (base_x, center_y), 255, thickness)

        # 基極垂直線（圓內）
        base_line_x = center_x - radius // 2
        cv2.line(img, (base_line_x, center_y - radius // 2),
                 (base_line_x, center_y + radius // 2), 255, thickness)

        # 集電極線（右上斜線）
        collector_start = (base_line_x, center_y - radius // 3)
        collector_end = (center_x + radius, center_y - radius)
        cv2.line(img, collector_start, collector_end, 255, thickness)

        # 發射極線（右下斜線 + 箭頭）
        emitter_start = (base_line_x, center_y + radius // 3)
        emitter_end = (center_x + radius, center_y + radius)
        cv2.line(img, emitter_start, emitter_end, 255, thickness)

        # 箭頭（發射極方向）
        arrow_len = radius // 3
        arrow_angle = 0.5  # 箭頭角度
        import math
        dx = emitter_end[0] - emitter_start[0]
        dy = emitter_end[1] - emitter_start[1]
        angle = math.atan2(dy, dx)
        # 箭頭兩側
        arrow1 = (int(emitter_end[0] - arrow_len * math.cos(angle - arrow_angle)),
                  int(emitter_end[1] - arrow_len * math.sin(angle - arrow_angle)))
        arrow2 = (int(emitter_end[0] - arrow_len * math.cos(angle + arrow_angle)),
                  int(emitter_end[1] - arrow_len * math.sin(angle + arrow_angle)))
        cv2.line(img, emitter_end, arrow1, 255, thickness)
        cv2.line(img, emitter_end, arrow2, 255, thickness)

        self._target_image = img
        return img

    def create_target_capacitor_image(self, thickness: int = 12) -> np.ndarray:
        """
        建立變壓器目標圖像
        兩組線圈（半圓弧）+ 中間雙線

        Args:
            thickness: 線條粗細

        Returns:
            變壓器形狀二值圖像
        """
        w, h = self.canvas_size
        img = np.zeros((h, w), dtype=np.uint8)

        center_x, center_y = w // 2, h // 2
        coil_radius = min(w, h) // 10
        coil_count = 3  # 每側線圈數量
        gap = min(w, h) // 8  # 兩側線圈間距

        # 左側線圈（3 個半圓弧，向左凸起）
        left_x = center_x - gap
        for i in range(coil_count):
            arc_y = center_y - (coil_count - 1) * coil_radius + i * 2 * coil_radius
            cv2.ellipse(img, (left_x, arc_y), (coil_radius, coil_radius),
                       0, 90, 270, 255, thickness)

        # 右側線圈（3 個半圓弧，向右凸起）
        right_x = center_x + gap
        for i in range(coil_count):
            arc_y = center_y - (coil_count - 1) * coil_radius + i * 2 * coil_radius
            cv2.ellipse(img, (right_x, arc_y), (coil_radius, coil_radius),
                       0, -90, 90, 255, thickness)

        # 中間兩條平行線（鐵芯）
        core_height = coil_count * 2 * coil_radius
        core_top = center_y - core_height // 2
        core_bottom = center_y + core_height // 2
        line_gap = gap // 3
        cv2.line(img, (center_x - line_gap // 2, core_top),
                 (center_x - line_gap // 2, core_bottom), 255, thickness)
        cv2.line(img, (center_x + line_gap // 2, core_top),
                 (center_x + line_gap // 2, core_bottom), 255, thickness)

        # 左側引線
        cv2.line(img, (left_x - coil_radius - w // 8, center_y - core_height // 3),
                 (left_x - coil_radius, center_y - core_height // 3), 255, thickness)
        cv2.line(img, (left_x - coil_radius - w // 8, center_y + core_height // 3),
                 (left_x - coil_radius, center_y + core_height // 3), 255, thickness)

        # 右側引線
        cv2.line(img, (right_x + coil_radius, center_y - core_height // 3),
                 (right_x + coil_radius + w // 8, center_y - core_height // 3), 255, thickness)
        cv2.line(img, (right_x + coil_radius, center_y + core_height // 3),
                 (right_x + coil_radius + w // 8, center_y + core_height // 3), 255, thickness)

        self._target_image = img
        return img

    def create_target_ic_image(self, thickness: int = 10) -> np.ndarray:
        """
        建立 IC 晶片（矩形 + 引腳）目標圖像
        矩形外框 + 四邊各 3 個引腳

        Args:
            thickness: 線條粗細

        Returns:
            IC 晶片形狀二值圖像
        """
        w, h = self.canvas_size
        img = np.zeros((h, w), dtype=np.uint8)

        margin = min(w, h) // 5
        pin_length = min(w, h) // 10

        # 主體矩形邊界
        rect_left = margin + pin_length
        rect_right = w - margin - pin_length
        rect_top = margin + pin_length
        rect_bottom = h - margin - pin_length

        # 繪製矩形外框
        cv2.rectangle(img, (rect_left, rect_top), (rect_right, rect_bottom), 255, thickness)

        # 每邊 3 個引腳
        num_pins = 3

        # 頂部引腳
        for i in range(num_pins):
            pin_x = rect_left + (rect_right - rect_left) * (i + 1) // (num_pins + 1)
            cv2.line(img, (pin_x, rect_top - pin_length), (pin_x, rect_top), 255, thickness)

        # 底部引腳
        for i in range(num_pins):
            pin_x = rect_left + (rect_right - rect_left) * (i + 1) // (num_pins + 1)
            cv2.line(img, (pin_x, rect_bottom), (pin_x, rect_bottom + pin_length), 255, thickness)

        # 左側引腳
        for i in range(num_pins):
            pin_y = rect_top + (rect_bottom - rect_top) * (i + 1) // (num_pins + 1)
            cv2.line(img, (rect_left - pin_length, pin_y), (rect_left, pin_y), 255, thickness)

        # 右側引腳
        for i in range(num_pins):
            pin_y = rect_top + (rect_bottom - rect_top) * (i + 1) // (num_pins + 1)
            cv2.line(img, (rect_right, pin_y), (rect_right + pin_length, pin_y), 255, thickness)

        self._target_image = img
        return img

    def create_target_opamp_image(self, thickness: int = 12) -> np.ndarray:
        """
        建立比較器電路目標圖像
        三角形 + 電源腳位 V+/V- + 輸入/輸出線

        Args:
            thickness: 線條粗細

        Returns:
            比較器電路形狀二值圖像
        """
        w, h = self.canvas_size
        img = np.zeros((h, w), dtype=np.uint8)

        center_x, center_y = w // 2, h // 2
        # 稍微縮小三角形高度以容納電源腳位
        tri_height = int(min(w, h) * 0.45)
        tri_width = int(tri_height * 0.75)

        # 三角形頂點（指向右邊）
        left_x = center_x - tri_width // 2
        right_x = center_x + tri_width // 2
        top_y = center_y - tri_height // 2
        bottom_y = center_y + tri_height // 2

        # 繪製三角形（左邊垂直線 + 上下斜線到右頂點）
        # 左邊垂直線
        cv2.line(img, (left_x, top_y), (left_x, bottom_y), 255, thickness)
        # 上斜線
        cv2.line(img, (left_x, top_y), (right_x, center_y), 255, thickness)
        # 下斜線
        cv2.line(img, (left_x, bottom_y), (right_x, center_y), 255, thickness)

        # 電源腳位
        power_len = tri_height // 4

        # V+ 電源線（三角形頂部中央向上延伸）
        vplus_x = center_x
        cv2.line(img, (vplus_x, top_y), (vplus_x, top_y - power_len), 255, thickness)

        # V- 接地線（三角形底部中央向下延伸）
        vminus_x = center_x
        cv2.line(img, (vminus_x, bottom_y), (vminus_x, bottom_y + power_len), 255, thickness)

        # 輸入線（+ 和 - 端）
        input_len = tri_width // 3
        plus_y = center_y - tri_height // 4
        minus_y = center_y + tri_height // 4

        # + 輸入線
        cv2.line(img, (left_x - input_len, plus_y), (left_x, plus_y), 255, thickness)
        # - 輸入線
        cv2.line(img, (left_x - input_len, minus_y), (left_x, minus_y), 255, thickness)

        # 輸出線
        cv2.line(img, (right_x, center_y), (right_x + input_len, center_y), 255, thickness)

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
        if shape_type == ShapeType.TRANSISTOR:
            return self.create_target_transistor_image(thickness)
        elif shape_type == ShapeType.CAPACITOR:
            return self.create_target_capacitor_image(thickness)
        elif shape_type == ShapeType.IC_CHIP:
            return self.create_target_ic_image(thickness)
        elif shape_type == ShapeType.OP_AMP:
            return self.create_target_opamp_image(thickness)
        else:
            # 預設返回 H 形
            return self.create_target_h_image(thickness)

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
