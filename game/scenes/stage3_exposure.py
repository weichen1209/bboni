"""
第三關：曝光顯影
玩家需要保持感測器穩定，模擬光刻機曝光過程
穩定度越高，曝光品質越好
"""

import pygame
import math
import random
import numpy as np
from typing import List
from collections import deque
from .base import Scene, Button, ProgressBar, ShapeCard
from ..config import *
from ..utils.cv_scoring import ShapeType, SHAPE_METADATA, ShapeSimilarityScorer


class ExposureStage(Scene):
    """曝光顯影關卡 - 保持穩定"""

    # 遊戲階段
    PHASE_SELECTION = 0     # 圖形選擇（新增）
    PHASE_INSTRUCTIONS = 1  # 操作說明
    PHASE_EXPOSURE = 2      # 曝光中
    PHASE_RESULT = 3        # 顯示結果

    # 曝光參數
    EXPOSURE_DURATION = 10.0      # 最長曝光時間 (秒)
    STABILITY_THRESHOLD = 0.6     # 穩定閾值 (低於此值顯示警告，已放寬)
    FILL_SPEED_STABLE = 0.15      # 穩定時進度填充速度
    FILL_SPEED_UNSTABLE = 0.02    # 不穩定時進度填充速度

    # 晶圓參數（與第四關一致）
    WAFER_RADIUS = 100            # 晶圓半徑 (像素)
    GRID_SIZE = 40                # 圖案網格解析度

    def __init__(self, game):
        super().__init__(game)

        # 遊戲階段
        self.phase = self.PHASE_INSTRUCTIONS

        # 曝光狀態
        self.exposure_elapsed = 0.0
        self.exposure_progress = 0.0     # 曝光進度 (0-1)
        self.stability_samples = []      # 穩定度樣本
        self.current_stability = 0.0

        # 晶圓中心位置
        self.wafer_center_x = SCREEN_WIDTH // 2
        self.wafer_center_y = 280

        # H 形目標圖案網格
        self.target_grid = [[False] * self.GRID_SIZE for _ in range(self.GRID_SIZE)]

        # 動畫
        self.uv_pulse = 0.0              # UV 光脈動動畫
        self.warning_flash = 0.0         # 警告閃爍
        self.particle_angle = 0.0

        # 穩定度平滑處理
        self._stability_history = []

        # 分數
        self.exposure_score = 0

        # UI 元件
        center_x = SCREEN_WIDTH // 2
        self.start_button = Button(
            center_x - 100, 550, 200, 50,
            "開始曝光", PRIMARY_COLOR
        )
        self.next_button = Button(
            center_x - 100, 620, 200, 50,
            "繼續", PRIMARY_COLOR
        )
        self.progress_bar = ProgressBar(
            center_x - 250, 580, 500, 30,
            bg_color=DARK_GRAY,
            fill_color=PHOTORESIST_PURPLE,
            border_color=GRAY
        )
        self.stability_bar = ProgressBar(
            center_x - 150, 520, 300, 20,
            bg_color=DARK_GRAY,
            fill_color=SECONDARY_COLOR,
            border_color=GRAY
        )

        # 字體
        self.title_font = None
        self.text_font = None
        self.small_font = None
        self.score_font = None

        # 圖形選擇相關
        self.shape_cards: List[ShapeCard] = []
        self.confirm_button = Button(
            SCREEN_WIDTH // 2 - 100, 580, 200, 50,
            "確定選擇", PRIMARY_COLOR
        )

    def on_enter(self):
        """進入場景"""
        super().on_enter()
        self.title_font = pygame.font.SysFont("Microsoft JhengHei", 42)
        self.text_font = pygame.font.SysFont("Microsoft JhengHei", 24)
        self.small_font = pygame.font.SysFont("Microsoft JhengHei", 18)
        self.score_font = pygame.font.SysFont("Microsoft JhengHei", 48)

        # 預繪製增強版漸層背景（暗紫色調）
        self._bg_surface = self.create_enhanced_background(UV_PURPLE, add_vignette=True, add_grid=False)

        # 環境粒子（UV光粒子）
        self.ambient_particles = []
        for _ in range(20):
            self.ambient_particles.append({
                'x': random.randint(0, SCREEN_WIDTH),
                'y': random.randint(0, SCREEN_HEIGHT),
                'vx': random.uniform(-5, 5),
                'vy': random.uniform(-10, -2),
                'size': random.uniform(1, 2),
                'alpha': random.randint(20, 50)
            })

        # 重置狀態 - 從選擇階段開始
        self.phase = self.PHASE_SELECTION
        self.exposure_elapsed = 0.0
        self.exposure_progress = 0.0
        self.stability_samples = []
        self.current_stability = 0.0
        self.exposure_score = 0
        self.uv_pulse = 0.0
        self.warning_flash = 0.0
        self._stability_history = []  # 重置穩定度歷史

        # 初始化圖形選擇卡片
        self._init_shape_cards()

    def handle_event(self, event: pygame.event.Event):
        """處理事件"""
        if self.phase == self.PHASE_SELECTION:
            self._handle_selection_event(event)
        elif self.phase == self.PHASE_INSTRUCTIONS:
            self._handle_instructions_event(event)
        elif self.phase == self.PHASE_EXPOSURE:
            self._handle_exposure_event(event)
        elif self.phase == self.PHASE_RESULT:
            self._handle_result_event(event)

        # ESC 返回選單
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.switch_to("menu")

    def _handle_selection_event(self, event: pygame.event.Event):
        """圖形選擇階段事件處理"""
        # 處理卡片點擊
        for card in self.shape_cards:
            if card.handle_event(event):
                # 取消所有選擇，選中當前卡片
                for c in self.shape_cards:
                    c.is_selected = False
                card.is_selected = True
                self.game.selected_shape_type = card.shape_type

        # 處理確認按鈕
        if self.confirm_button.handle_event(event):
            self._confirm_selection()

        # 鍵盤導航
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                self._confirm_selection()
            elif event.key == pygame.K_LEFT:
                self._select_prev_shape()
            elif event.key == pygame.K_RIGHT:
                self._select_next_shape()

    def _handle_instructions_event(self, event: pygame.event.Event):
        """指示階段事件處理"""
        if self.start_button.handle_event(event):
            self._start_exposure()

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE or event.key == pygame.K_RETURN:
                self._start_exposure()

    def _handle_exposure_event(self, event: pygame.event.Event):
        """曝光階段事件處理"""
        pass  # 曝光期間不需要特別事件處理

    def _handle_result_event(self, event: pygame.event.Event):
        """結果階段事件處理"""
        if self.next_button.handle_event(event):
            self._finish_stage()

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE or event.key == pygame.K_RETURN:
                self._finish_stage()

    def _init_shape_cards(self):
        """初始化圖形選擇卡片"""
        shapes = [
            ShapeType.TRANSISTOR,
            ShapeType.CAPACITOR,
            ShapeType.IC_CHIP,
            ShapeType.OP_AMP,
        ]

        card_width = 180
        card_height = 220
        spacing = 30
        total_width = len(shapes) * card_width + (len(shapes) - 1) * spacing
        start_x = (SCREEN_WIDTH - total_width) // 2
        card_y = 180

        # 建立臨時評分器來生成縮圖
        temp_scorer = ShapeSimilarityScorer((140, 100))

        self.shape_cards = []
        for i, shape_type in enumerate(shapes):
            x = start_x + i * (card_width + spacing)

            # 生成縮圖
            thumb_img = temp_scorer.get_thumbnail(shape_type, (140, 100))

            # 將灰階圖轉為紫色 RGB（配合曝光主題）
            thumb_rgb = np.zeros((100, 140, 3), dtype=np.uint8)
            thumb_rgb[:, :, 0] = thumb_img // 2      # R
            thumb_rgb[:, :, 1] = thumb_img // 4      # G
            thumb_rgb[:, :, 2] = thumb_img           # B (紫色為主)

            # 轉換為 pygame surface
            thumb_surface = pygame.image.frombuffer(
                thumb_rgb.tobytes(), (140, 100), "RGB"
            )

            metadata = SHAPE_METADATA[shape_type]
            card = ShapeCard(x, card_y, card_width, card_height, shape_type, metadata, thumb_surface)
            self.shape_cards.append(card)

        # 使用 game 中儲存的選擇（或預設第一個）
        selected_type = self.game.selected_shape_type
        for card in self.shape_cards:
            card.is_selected = (card.shape_type == selected_type)

    def _confirm_selection(self):
        """確認圖形選擇，進入說明階段"""
        # 生成選擇的圖形
        self._generate_target_pattern()
        self.phase = self.PHASE_INSTRUCTIONS

    def _select_prev_shape(self):
        """選擇上一個圖形"""
        current_index = 0
        for i, card in enumerate(self.shape_cards):
            if card.is_selected:
                current_index = i
                card.is_selected = False
                break

        new_index = (current_index - 1) % len(self.shape_cards)
        self.shape_cards[new_index].is_selected = True
        self.game.selected_shape_type = self.shape_cards[new_index].shape_type

    def _select_next_shape(self):
        """選擇下一個圖形"""
        current_index = 0
        for i, card in enumerate(self.shape_cards):
            if card.is_selected:
                current_index = i
                card.is_selected = False
                break

        new_index = (current_index + 1) % len(self.shape_cards)
        self.shape_cards[new_index].is_selected = True
        self.game.selected_shape_type = self.shape_cards[new_index].shape_type

    def _start_exposure(self):
        """開始曝光階段"""
        self.phase = self.PHASE_EXPOSURE
        self.exposure_elapsed = 0.0
        self.exposure_progress = 0.0
        self.stability_samples = []

    def _finish_exposure(self):
        """完成曝光，進入結果階段"""
        self.exposure_score = self._calculate_score()
        self.game.scores["exposure"] = self.exposure_score
        self.phase = self.PHASE_RESULT

    def _finish_stage(self):
        """完成關卡，進入下一關"""
        # 檢查 stage4 是否存在，否則進入 result
        if "stage4" in self.game.scenes:
            self.switch_to("stage4")
        else:
            self.switch_to("result")

    def _generate_target_pattern(self):
        """根據選擇的圖形類型生成目標圖案"""
        shape_type = self.game.selected_shape_type

        # 清空網格
        for y in range(self.GRID_SIZE):
            for x in range(self.GRID_SIZE):
                self.target_grid[y][x] = False

        if shape_type == ShapeType.TRANSISTOR:
            self._generate_transistor_pattern()
        elif shape_type == ShapeType.CAPACITOR:
            self._generate_capacitor_pattern()
        elif shape_type == ShapeType.IC_CHIP:
            self._generate_ic_pattern()
        elif shape_type == ShapeType.OP_AMP:
            self._generate_opamp_pattern()
        else:
            self._generate_transistor_pattern()  # 預設

    def _generate_transistor_pattern(self):
        """生成 NPN 電晶體圖案（圓形 + 基極 + 集電極/發射極）"""
        center = self.GRID_SIZE // 2
        radius = 8

        # 繪製圓形外框
        for y in range(self.GRID_SIZE):
            for x in range(self.GRID_SIZE):
                dx = x - center
                dy = y - center
                dist = math.sqrt(dx * dx + dy * dy)
                if radius - 1.5 <= dist <= radius + 1.5:
                    if self._is_in_wafer_grid(x, y):
                        self.target_grid[y][x] = True

        # 基極線（左側水平線）
        for x in range(center - radius - 6, center - radius + 1):
            for y in range(center - 1, center + 2):
                if self._is_in_wafer_grid(x, y):
                    self.target_grid[y][x] = True

        # 基極垂直線（圓內）
        base_x = center - radius // 2
        for y in range(center - radius // 2, center + radius // 2 + 1):
            for x in range(base_x - 1, base_x + 2):
                if self._is_in_wafer_grid(x, y):
                    self.target_grid[y][x] = True

        # 集電極線（右上斜線）
        for i in range(10):
            x = base_x + i
            y = center - radius // 3 - i
            for dx in range(-1, 2):
                for dy in range(-1, 2):
                    if self._is_in_wafer_grid(x + dx, y + dy):
                        self.target_grid[y + dy][x + dx] = True

        # 發射極線（右下斜線）
        for i in range(10):
            x = base_x + i
            y = center + radius // 3 + i
            for dx in range(-1, 2):
                for dy in range(-1, 2):
                    if self._is_in_wafer_grid(x + dx, y + dy):
                        self.target_grid[y + dy][x + dx] = True

    def _generate_capacitor_pattern(self):
        """生成變壓器圖案（兩組線圈 + 鐵芯）"""
        center = self.GRID_SIZE // 2
        coil_radius = 3
        coil_count = 3
        gap = 4

        # 左側線圈（3 個半圓弧效果）
        left_x = center - gap
        for i in range(coil_count):
            arc_y = center - (coil_count - 1) * coil_radius + i * 2 * coil_radius
            # 繪製半圓（左凸）
            for angle in range(90, 271):
                rad = math.radians(angle)
                x = int(left_x + coil_radius * math.cos(rad))
                y = int(arc_y + coil_radius * math.sin(rad))
                for dx in range(-1, 2):
                    for dy in range(-1, 2):
                        if self._is_in_wafer_grid(x + dx, y + dy):
                            self.target_grid[y + dy][x + dx] = True

        # 右側線圈（3 個半圓弧效果）
        right_x = center + gap
        for i in range(coil_count):
            arc_y = center - (coil_count - 1) * coil_radius + i * 2 * coil_radius
            # 繪製半圓（右凸）
            for angle in range(-90, 91):
                rad = math.radians(angle)
                x = int(right_x + coil_radius * math.cos(rad))
                y = int(arc_y + coil_radius * math.sin(rad))
                for dx in range(-1, 2):
                    for dy in range(-1, 2):
                        if self._is_in_wafer_grid(x + dx, y + dy):
                            self.target_grid[y + dy][x + dx] = True

        # 中間鐵芯（兩條平行線）
        core_height = coil_count * 2 * coil_radius
        for y in range(center - core_height // 2, center + core_height // 2 + 1):
            for x in range(center - 1, center):
                if self._is_in_wafer_grid(x, y):
                    self.target_grid[y][x] = True
            for x in range(center + 1, center + 2):
                if self._is_in_wafer_grid(x, y):
                    self.target_grid[y][x] = True

    def _generate_ic_pattern(self):
        """生成 IC 晶片圖案（矩形 + 引腳）"""
        center = self.GRID_SIZE // 2
        half_width = 2
        rect_size = 8
        pin_length = 4

        # 矩形外框（四邊）
        # 頂邊
        for y in range(center - rect_size - half_width, center - rect_size + half_width + 1):
            for x in range(center - rect_size, center + rect_size + 1):
                if self._is_in_wafer_grid(x, y):
                    self.target_grid[y][x] = True
        # 底邊
        for y in range(center + rect_size - half_width, center + rect_size + half_width + 1):
            for x in range(center - rect_size, center + rect_size + 1):
                if self._is_in_wafer_grid(x, y):
                    self.target_grid[y][x] = True
        # 左邊
        for y in range(center - rect_size, center + rect_size + 1):
            for x in range(center - rect_size - half_width, center - rect_size + half_width + 1):
                if self._is_in_wafer_grid(x, y):
                    self.target_grid[y][x] = True
        # 右邊
        for y in range(center - rect_size, center + rect_size + 1):
            for x in range(center + rect_size - half_width, center + rect_size + half_width + 1):
                if self._is_in_wafer_grid(x, y):
                    self.target_grid[y][x] = True

        # 引腳（每邊 3 個）
        pin_positions = [-5, 0, 5]
        for offset in pin_positions:
            # 頂部引腳
            for y in range(center - rect_size - pin_length, center - rect_size):
                for x in range(center + offset - 1, center + offset + 2):
                    if self._is_in_wafer_grid(x, y):
                        self.target_grid[y][x] = True
            # 底部引腳
            for y in range(center + rect_size + 1, center + rect_size + pin_length + 1):
                for x in range(center + offset - 1, center + offset + 2):
                    if self._is_in_wafer_grid(x, y):
                        self.target_grid[y][x] = True
            # 左側引腳
            for y in range(center + offset - 1, center + offset + 2):
                for x in range(center - rect_size - pin_length, center - rect_size):
                    if self._is_in_wafer_grid(x, y):
                        self.target_grid[y][x] = True
            # 右側引腳
            for y in range(center + offset - 1, center + offset + 2):
                for x in range(center + rect_size + 1, center + rect_size + pin_length + 1):
                    if self._is_in_wafer_grid(x, y):
                        self.target_grid[y][x] = True

    def _generate_opamp_pattern(self):
        """生成比較器電路圖案（三角形 + 電源腳位 V+/V- + 輸入輸出線）"""
        center = self.GRID_SIZE // 2
        # 加大尺寸以容納電源腳位
        tri_height = 16
        tri_width = 12

        # 三角形頂點座標
        left_x = center - tri_width // 2
        right_x = center + tri_width // 2
        top_y = center - tri_height // 2
        bottom_y = center + tri_height // 2

        # 1. 左邊垂直線
        for y in range(top_y, bottom_y + 1):
            for x in range(left_x - 1, left_x + 2):
                if self._is_in_wafer_grid(x, y):
                    self.target_grid[y][x] = True

        # 2. 上斜線（左上到右中）
        for i in range(tri_width + 2):
            x = left_x + i
            y = top_y + (tri_height // 2) * i // tri_width
            for dx in range(-1, 2):
                for dy in range(-1, 2):
                    if self._is_in_wafer_grid(x + dx, y + dy):
                        self.target_grid[y + dy][x + dx] = True

        # 3. 下斜線（左下到右中）
        for i in range(tri_width + 2):
            x = left_x + i
            y = bottom_y - (tri_height // 2) * i // tri_width
            for dx in range(-1, 2):
                for dy in range(-1, 2):
                    if self._is_in_wafer_grid(x + dx, y + dy):
                        self.target_grid[y + dy][x + dx] = True

        # 4. V+ 電源線（三角形頂部中央向上延伸）
        vplus_x = center
        vplus_len = 5
        for y in range(top_y - vplus_len, top_y + 1):
            for x in range(vplus_x - 1, vplus_x + 2):
                if self._is_in_wafer_grid(x, y):
                    self.target_grid[y][x] = True

        # 5. V- 接地線（三角形底部中央向下延伸）
        vminus_x = center
        vminus_len = 5
        for y in range(bottom_y, bottom_y + vminus_len + 1):
            for x in range(vminus_x - 1, vminus_x + 2):
                if self._is_in_wafer_grid(x, y):
                    self.target_grid[y][x] = True

        # 6. + 輸入線（左側上方）
        plus_y = center - tri_height // 4
        for x in range(left_x - 6, left_x):
            for y in range(plus_y - 1, plus_y + 2):
                if self._is_in_wafer_grid(x, y):
                    self.target_grid[y][x] = True

        # 7. - 輸入線（左側下方）
        minus_y = center + tri_height // 4
        for x in range(left_x - 6, left_x):
            for y in range(minus_y - 1, minus_y + 2):
                if self._is_in_wafer_grid(x, y):
                    self.target_grid[y][x] = True

        # 8. 輸出線（右側）
        for x in range(right_x, right_x + 6):
            for y in range(center - 1, center + 2):
                if self._is_in_wafer_grid(x, y):
                    self.target_grid[y][x] = True

    def _is_in_wafer_grid(self, gx: int, gy: int) -> bool:
        """檢查網格座標是否在晶圓範圍內"""
        if gx < 0 or gx >= self.GRID_SIZE or gy < 0 or gy >= self.GRID_SIZE:
            return False

        # 轉換為相對於中心的座標
        center = self.GRID_SIZE // 2
        dx = gx - center
        dy = gy - center

        # 檢查是否在圓形範圍內
        grid_radius = self.GRID_SIZE // 2 - 2
        return (dx * dx + dy * dy) <= (grid_radius * grid_radius)

    def _grid_to_pixel(self, gx: int, gy: int) -> tuple:
        """將網格座標轉換為像素座標"""
        grid_center = self.GRID_SIZE // 2
        scale = (self.WAFER_RADIUS * 2) / self.GRID_SIZE

        px = self.wafer_center_x + (gx - grid_center) * scale
        py = self.wafer_center_y + (gy - grid_center) * scale

        return (px, py)

    def _get_stability(self) -> float:
        """取得穩定度（使用陀螺儀檢測旋轉運動）"""
        if self.game.sensor and self.game.sensor.is_connected:
            data = self.game.sensor.get_imu_data()

            # 使用陀螺儀檢測旋轉運動（靈敏度: 16.4 LSB/dps）
            gyro_magnitude = (data.gx ** 2 + data.gy ** 2 + data.gz ** 2) ** 0.5
            gyro_dps = gyro_magnitude / 16.4  # 轉換為 度/秒

            # 死區：< 5 dps 視為完全穩定
            if gyro_dps < 5:
                raw_stability = 1.0
            else:
                # 5-30 dps 線性映射到 1.0-0.0
                raw_stability = max(0.0, 1.0 - (gyro_dps - 5) / 25)

            # 使用移動平均平滑化（最近 5 個樣本）
            self._stability_history.append(raw_stability)
            if len(self._stability_history) > 5:
                self._stability_history.pop(0)
            return sum(self._stability_history) / len(self._stability_history)
        return 1.0  # 裝置未連接時視為穩定

    def _calculate_score(self) -> int:
        """計算曝光品質分數"""
        if len(self.stability_samples) < 10:
            return 50  # 樣本不足給基本分

        # 計算平均穩定度
        avg_stability = sum(self.stability_samples) / len(self.stability_samples)

        # 計算穩定度一致性（標準差越小越好）
        variance = sum((s - avg_stability) ** 2 for s in self.stability_samples) / len(self.stability_samples)
        std_dev = variance ** 0.5

        # 基礎分數 = 平均穩定度 * 80
        base_score = avg_stability * 80

        # 一致性獎勵 = (1 - 標準差) * 20
        consistency_bonus = max(0, (1 - std_dev)) * 20

        total = int(base_score + consistency_bonus)
        return max(0, min(100, total))

    def update(self, dt: float):
        """更新遊戲邏輯"""
        # 更新淡入淡出
        self.update_fade(dt)

        # 更新動畫
        self.uv_pulse += dt * 5
        self.particle_angle += dt * 30

        # 更新按鈕動畫
        self.start_button.update(dt)
        self.next_button.update(dt)
        self.confirm_button.update(dt)

        # 更新進度條動畫
        self.progress_bar.update(dt)
        self.stability_bar.update(dt)

        # 更新環境粒子
        self._update_ambient_particles(dt)

        if self.phase == self.PHASE_SELECTION:
            # 更新卡片動畫
            for card in self.shape_cards:
                card.update(dt)
        elif self.phase == self.PHASE_INSTRUCTIONS:
            pass  # 等待使用者開始
        elif self.phase == self.PHASE_EXPOSURE:
            self._update_exposure_phase(dt)
        elif self.phase == self.PHASE_RESULT:
            pass

    def _update_ambient_particles(self, dt: float):
        """更新環境粒子"""
        for p in self.ambient_particles:
            p['x'] += p['vx'] * dt
            p['y'] += p['vy'] * dt
            if p['y'] < -10:
                p['y'] = SCREEN_HEIGHT + 10
                p['x'] = random.randint(0, SCREEN_WIDTH)
            if p['x'] < -10:
                p['x'] = SCREEN_WIDTH + 10
            elif p['x'] > SCREEN_WIDTH + 10:
                p['x'] = -10

    def _update_exposure_phase(self, dt: float):
        """曝光階段更新"""
        # 更新經過時間
        self.exposure_elapsed += dt

        # 取得當前穩定度
        self.current_stability = self._get_stability()
        self.stability_samples.append(self.current_stability)

        # 更新穩定度顯示條
        self.stability_bar.set_progress(self.current_stability)

        # 根據穩定度更新曝光進度
        if self.current_stability >= self.STABILITY_THRESHOLD:
            self.exposure_progress += self.FILL_SPEED_STABLE * dt
            self.warning_flash = max(0, self.warning_flash - dt * 3)
        else:
            self.exposure_progress += self.FILL_SPEED_UNSTABLE * dt
            self.warning_flash = min(1, self.warning_flash + dt * 5)

        # 更新進度條
        self.progress_bar.set_progress(self.exposure_progress)

        # 檢查是否完成
        if self.exposure_progress >= 1.0 or self.exposure_elapsed >= self.EXPOSURE_DURATION:
            self._finish_exposure()

    def draw(self, screen: pygame.Surface):
        """繪製場景"""
        self._draw_background(screen)

        # 環境粒子
        self._draw_ambient_particles(screen)

        if self.phase == self.PHASE_SELECTION:
            self._draw_selection(screen)
        elif self.phase == self.PHASE_INSTRUCTIONS:
            self._draw_instructions(screen)
        elif self.phase == self.PHASE_EXPOSURE:
            self._draw_exposure_phase(screen)
        elif self.phase == self.PHASE_RESULT:
            self._draw_result(screen)

        # 淡入淡出遮罩
        self.draw_fade_overlay(screen)

    def _draw_selection(self, screen: pygame.Surface):
        """繪製圖形選擇畫面"""
        # 標題
        self.draw_title(screen, "選擇電路圖案", y=60, font=self.title_font)

        # 副標題
        subtitle = self.text_font.render(
            "選擇要繪製的半導體電路圖案", True, TEXT_SECONDARY
        )
        subtitle_rect = subtitle.get_rect(center=(SCREEN_WIDTH // 2, 120))
        screen.blit(subtitle, subtitle_rect)

        # 繪製圖形選擇卡片
        for card in self.shape_cards:
            card.draw(screen, self.text_font, self.small_font)

        # 已選擇的圖形資訊
        selected_meta = SHAPE_METADATA[self.game.selected_shape_type]
        status = f"已選擇: {selected_meta['display_name']}"
        status_surface = self.text_font.render(status, True, SECONDARY_COLOR)
        status_rect = status_surface.get_rect(center=(SCREEN_WIDTH // 2, 450))
        screen.blit(status_surface, status_rect)

        # 圖形描述
        desc = selected_meta["description"]
        desc_surface = self.small_font.render(desc, True, TEXT_MUTED)
        desc_rect = desc_surface.get_rect(center=(SCREEN_WIDTH // 2, 490))
        screen.blit(desc_surface, desc_rect)

        # 鍵盤提示
        hint = "使用 ← → 選擇，Enter 確定"
        hint_surface = self.small_font.render(hint, True, TEXT_MUTED)
        hint_rect = hint_surface.get_rect(center=(SCREEN_WIDTH // 2, 530))
        screen.blit(hint_surface, hint_rect)

        # 確認按鈕
        self.confirm_button.draw(screen)

    def _draw_ambient_particles(self, screen: pygame.Surface):
        """繪製環境粒子"""
        for p in self.ambient_particles:
            surf = pygame.Surface((int(p['size'] * 2), int(p['size'] * 2)), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*UV_PURPLE_GLOW, p['alpha']),
                             (int(p['size']), int(p['size'])), int(p['size']))
            screen.blit(surf, (int(p['x'] - p['size']), int(p['y'] - p['size'])))

    def _draw_background(self, screen: pygame.Surface):
        """繪製漸層背景（使用預繪製的快取）"""
        screen.blit(self._bg_surface, (0, 0))

    def _draw_instructions(self, screen: pygame.Surface):
        """繪製指示畫面"""
        # 標題（帶光暈）
        self.draw_title(screen, "曝光顯影 - 保持穩定", y=80, font=self.title_font)

        # 晶圓預覽
        self._draw_wafer_preview(screen, SCREEN_WIDTH // 2, 280)

        # 說明文字
        instructions = [
            "保持裝置穩定，讓UV光均勻曝光晶圓",
            "穩定度越高，曝光進度越快",
            "晃動會降低曝光品質！"
        ]

        y_start = 420
        for i, text in enumerate(instructions):
            surface = self.text_font.render(text, True, TEXT_SECONDARY)
            rect = surface.get_rect(center=(SCREEN_WIDTH // 2, y_start + i * 35))
            screen.blit(surface, rect)

        # 開始按鈕
        self.start_button.draw(screen)

    def _draw_exposure_phase(self, screen: pygame.Surface):
        """繪製曝光階段"""
        # 標題
        title = self.title_font.render("曝光中 - 保持穩定！", True, WHITE)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 40))
        screen.blit(title, title_rect)

        # UV 光效果
        self._draw_uv_light(screen)

        # 晶圓（曝光中）
        self._draw_wafer_exposing(screen, SCREEN_WIDTH // 2, 280)

        # 穩定度顯示
        stability_label = "穩定度："
        if self.current_stability >= self.STABILITY_THRESHOLD:
            stability_label += "良好"
            label_color = SECONDARY_COLOR
        else:
            stability_label += "不穩定！"
            label_color = DANGER_COLOR

        stability_text = self.text_font.render(stability_label, True, label_color)
        stability_rect = stability_text.get_rect(center=(SCREEN_WIDTH // 2, 490))
        screen.blit(stability_text, stability_rect)

        self.stability_bar.draw(screen)

        # 警告效果
        if self.warning_flash > 0:
            warning_alpha = int(150 * self.warning_flash * (0.5 + 0.5 * math.sin(self.uv_pulse * 3)))
            warning_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            warning_surf.fill((255, 0, 0, warning_alpha))
            screen.blit(warning_surf, (0, 0))

            warning_text = self.title_font.render("請保持穩定！", True, DANGER_COLOR)
            warning_rect = warning_text.get_rect(center=(SCREEN_WIDTH // 2, 450))
            screen.blit(warning_text, warning_rect)

        # 曝光進度
        progress_label = f"曝光進度: {int(self.exposure_progress * 100)}%"
        progress_text = self.text_font.render(progress_label, True, WHITE)
        progress_rect = progress_text.get_rect(center=(SCREEN_WIDTH // 2, 555))
        screen.blit(progress_text, progress_rect)

        self.progress_bar.draw(screen)

        # 提示
        hint = "保持裝置穩定！"
        hint_surface = self.small_font.render(hint, True, LIGHT_GRAY)
        hint_rect = hint_surface.get_rect(center=(SCREEN_WIDTH // 2, 650))
        screen.blit(hint_surface, hint_rect)

    def _draw_result(self, screen: pygame.Surface):
        """繪製結果畫面"""
        # 標題
        title = self.title_font.render("曝光完成！", True, WHITE)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 50))
        screen.blit(title, title_rect)

        # 完成的晶圓
        self._draw_wafer_complete(screen, SCREEN_WIDTH // 2, 280)

        # 分數顯示
        score_color = SECONDARY_COLOR if self.exposure_score >= 70 else ACCENT_COLOR if self.exposure_score >= 40 else DANGER_COLOR
        score_text = f"曝光品質: {self.exposure_score} 分"
        score_surface = self.score_font.render(score_text, True, score_color)
        score_rect = score_surface.get_rect(center=(SCREEN_WIDTH // 2, 480))
        screen.blit(score_surface, score_rect)

        # 詳細說明
        if self.exposure_score >= 80:
            detail = "優秀！曝光均勻，圖案清晰"
        elif self.exposure_score >= 60:
            detail = "良好，但有些微晃動痕跡"
        else:
            detail = "曝光不均勻，需要改進穩定度"

        detail_surface = self.text_font.render(detail, True, LIGHT_GRAY)
        detail_rect = detail_surface.get_rect(center=(SCREEN_WIDTH // 2, 530))
        screen.blit(detail_surface, detail_rect)

        # 繼續按鈕
        self.next_button.draw(screen)

    def _draw_uv_light(self, screen: pygame.Surface):
        """繪製UV光效果"""
        center_x = SCREEN_WIDTH // 2
        center_y = 100

        # UV 光源
        pulse = 0.7 + 0.3 * math.sin(self.uv_pulse)
        base_radius = int(60 * pulse)

        # 光暈層
        for i in range(5, 0, -1):
            alpha = int(30 * pulse * (6 - i) / 5)
            radius = base_radius + i * 20
            surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            color = (*PHOTORESIST_PURPLE, alpha)
            pygame.draw.circle(surf, color, (radius, radius), radius)
            screen.blit(surf, (center_x - radius, center_y - radius))

        # 光束
        if self.current_stability >= self.STABILITY_THRESHOLD:
            beam_width = 200
            beam_alpha = int(80 * pulse)
        else:
            beam_width = 200 + int(50 * math.sin(self.uv_pulse * 5))
            beam_alpha = int(40 * pulse)

        beam_surf = pygame.Surface((beam_width, 200), pygame.SRCALPHA)
        pygame.draw.polygon(beam_surf, (*PHOTORESIST_PURPLE, beam_alpha), [
            (beam_width // 2, 0),
            (0, 200),
            (beam_width, 200)
        ])
        screen.blit(beam_surf, (center_x - beam_width // 2, center_y + 30))

    def _draw_wafer_preview(self, screen: pygame.Surface, cx: int, cy: int):
        """繪製晶圓預覽（含 H 形目標圖案）"""
        radius = self.WAFER_RADIUS

        # 晶圓底座
        pygame.draw.circle(screen, DARK_GRAY, (cx, cy), radius + 5)

        # 晶圓本體
        pygame.draw.circle(screen, SILICON_BLUE, (cx, cy), radius)

        # 繪製 H 形目標圖案（光阻層）
        cell_size = (radius * 2) / self.GRID_SIZE
        for gy in range(self.GRID_SIZE):
            for gx in range(self.GRID_SIZE):
                if not self._is_in_wafer_grid(gx, gy):
                    continue
                if self.target_grid[gy][gx]:
                    px, py = self._grid_to_pixel(gx, gy)
                    surf = pygame.Surface((cell_size + 1, cell_size + 1), pygame.SRCALPHA)
                    surf.fill((*PHOTORESIST_PURPLE, 180))
                    screen.blit(surf, (px - cell_size / 2, py - cell_size / 2))

        # 邊框
        pygame.draw.circle(screen, WHITE, (cx, cy), radius, 2)

    def _draw_wafer_exposing(self, screen: pygame.Surface, cx: int, cy: int):
        """繪製曝光中的晶圓（含 H 形曝光效果）"""
        radius = self.WAFER_RADIUS

        # 晶圓底座
        pygame.draw.circle(screen, DARK_GRAY, (cx, cy), radius + 5)

        # 晶圓本體
        pygame.draw.circle(screen, SILICON_BLUE, (cx, cy), radius)

        # 繪製 H 形圖案曝光效果
        cell_size = (radius * 2) / self.GRID_SIZE
        pulse = 0.8 + 0.2 * math.sin(self.uv_pulse)

        for gy in range(self.GRID_SIZE):
            for gx in range(self.GRID_SIZE):
                if not self._is_in_wafer_grid(gx, gy):
                    continue
                if self.target_grid[gy][gx]:
                    px, py = self._grid_to_pixel(gx, gy)

                    # 根據曝光進度決定顏色
                    if self.exposure_progress > 0:
                        # 已曝光部分：亮紫色脈動
                        exposed_alpha = int(180 + 50 * pulse * self.exposure_progress)
                        exposed_color = (
                            int(PHOTORESIST_PURPLE[0] * pulse),
                            int(PHOTORESIST_PURPLE[1] * pulse),
                            int(min(255, PHOTORESIST_PURPLE[2] * (1 + 0.3 * self.exposure_progress))),
                            min(255, exposed_alpha)
                        )
                    else:
                        # 未曝光：暗紫色
                        exposed_color = (*PHOTORESIST_PURPLE, 150)

                    surf = pygame.Surface((cell_size + 1, cell_size + 1), pygame.SRCALPHA)
                    surf.fill(exposed_color)
                    screen.blit(surf, (px - cell_size / 2, py - cell_size / 2))

        # 穩定度視覺化 - 晃動時晶圓邊緣模糊
        if self.current_stability < self.STABILITY_THRESHOLD:
            shake = int(5 * (1 - self.current_stability))
            for i in range(3):
                offset_x = int(shake * math.sin(self.uv_pulse + i))
                offset_y = int(shake * math.cos(self.uv_pulse + i))
                blur_surf = pygame.Surface((radius * 2 + 20, radius * 2 + 20), pygame.SRCALPHA)
                pygame.draw.circle(blur_surf, (255, 0, 0, 30), (radius + 10, radius + 10), radius + 5, 2)
                screen.blit(blur_surf, (cx - radius - 10 + offset_x, cy - radius - 10 + offset_y))

        # 邊框
        pygame.draw.circle(screen, WHITE, (cx, cy), radius, 2)

    def _draw_wafer_complete(self, screen: pygame.Surface, cx: int, cy: int):
        """繪製完成的晶圓（含 H 形曝光結果）"""
        radius = self.WAFER_RADIUS

        # 晶圓底座
        pygame.draw.circle(screen, DARK_GRAY, (cx, cy), radius + 5)

        # 晶圓本體
        pygame.draw.circle(screen, SILICON_BLUE, (cx, cy), radius)

        # 曝光後的 H 形圖案（根據分數決定品質）
        quality = self.exposure_score / 100
        cell_size = (radius * 2) / self.GRID_SIZE

        # 根據品質決定圖案顏色
        if quality > 0.7:
            pattern_color = SECONDARY_COLOR
        elif quality > 0.4:
            pattern_color = ACCENT_COLOR
        else:
            pattern_color = DANGER_COLOR

        for gy in range(self.GRID_SIZE):
            for gx in range(self.GRID_SIZE):
                if not self._is_in_wafer_grid(gx, gy):
                    continue
                if self.target_grid[gy][gx]:
                    px, py = self._grid_to_pixel(gx, gy)
                    # 根據品質決定透明度
                    alpha = int(180 + 70 * quality)
                    surf = pygame.Surface((cell_size + 1, cell_size + 1), pygame.SRCALPHA)
                    surf.fill((*pattern_color, alpha))
                    screen.blit(surf, (px - cell_size / 2, py - cell_size / 2))

        # 邊框
        pygame.draw.circle(screen, WHITE, (cx, cy), radius, 3)

        # 品質標籤
        if quality > 0.7:
            label = "優質"
            label_color = SECONDARY_COLOR
        elif quality > 0.4:
            label = "合格"
            label_color = ACCENT_COLOR
        else:
            label = "不良"
            label_color = DANGER_COLOR

        label_surface = self.small_font.render(label, True, label_color)
        label_rect = label_surface.get_rect(center=(cx, cy + radius + 25))
        screen.blit(label_surface, label_rect)
