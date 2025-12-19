"""
OpenCV 圓形相似度評分模組
用於 Stage 2 薄膜沉積關卡的圓形繪製評分
"""

import cv2
import numpy as np
from typing import List, Tuple, Optional


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
