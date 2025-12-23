"""
第四關：蝕刻
玩家透過傾斜控制蝕刻方向，搖晃控制蝕刻速度
目標是精確地蝕刻出電路圖案
"""

import pygame
import math
import random
from .base import Scene, Button, ProgressBar
from ..config import *


class EtchingStage(Scene):
    """蝕刻關卡 - 傾斜控制方向，搖晃控制速度"""

    # 遊戲階段
    PHASE_INSTRUCTIONS = 0
    PHASE_ETCHING = 1
    PHASE_RESULT = 2

    # 蝕刻參數
    ETCHING_DURATION = 20.0       # 蝕刻時間限制 (秒)
    WAFER_RADIUS = 150            # 晶圓半徑 (像素)
    GRID_SIZE = 40                # 圖案網格解析度

    # 陀螺儀參數（與 Stage 2 一致）
    GYRO_DEADZONE = 300           # 死區（濾除平放時的雜訊）
    GYRO_MAX = 2000               # 最大有效值
    CURSOR_MAX_SPEED = 300.0      # 最大移動速度（像素/秒）
    CURSOR_MIN_SPEED = 50.0       # 最小移動速度（像素/秒）

    # 蝕刻參數
    ETCH_RATE_BASE = 0.3          # 基礎蝕刻速率
    ETCH_RATE_MAX = 1.5           # 最大蝕刻速率
    BRUSH_RADIUS_BASE = 1         # 基礎蝕刻筆刷半徑
    BRUSH_RADIUS_MAX = 2          # 最大蝕刻筆刷半徑

    def __init__(self, game):
        super().__init__(game)

        # 遊戲階段
        self.phase = self.PHASE_INSTRUCTIONS

        # 晶圓中心位置
        self.wafer_center_x = SCREEN_WIDTH // 2
        self.wafer_center_y = 300

        # 游標位置
        self.cursor_x = float(self.wafer_center_x)
        self.cursor_y = float(self.wafer_center_y)
        self.cursor_velocity_x = 0.0
        self.cursor_velocity_y = 0.0

        # 圖案網格
        # target_grid: 目標蝕刻區域 (True = 需要蝕刻)
        # etched_grid: 已蝕刻深度 (0.0 ~ 1.0)
        self.target_grid = [[False] * self.GRID_SIZE for _ in range(self.GRID_SIZE)]
        self.etched_grid = [[0.0] * self.GRID_SIZE for _ in range(self.GRID_SIZE)]

        # 計時器
        self.etching_elapsed = 0.0

        # 當前蝕刻強度
        self.current_intensity = 0.0

        # 分數
        self.coverage_score = 0
        self.accuracy_score = 0
        self.uniformity_score = 0
        self.precision_score = 0

        # 粒子效果
        self.plasma_particles = []

        # 動畫
        self.pulse_animation = 0.0
        self.cursor_glow = 0.0

        # UI 元件
        center_x = SCREEN_WIDTH // 2
        self.start_button = Button(
            center_x - 100, 580, 200, 50,
            "開始蝕刻", PRIMARY_COLOR
        )
        self.next_button = Button(
            center_x - 100, 620, 200, 50,
            "查看結果", PRIMARY_COLOR
        )
        self.timer_bar = ProgressBar(
            center_x - 250, 70, 500, 20,
            bg_color=DARK_GRAY,
            fill_color=ACCENT_COLOR,
            border_color=GRAY
        )
        self.intensity_bar = ProgressBar(
            center_x - 150, 540, 300, 15,
            bg_color=DARK_GRAY,
            fill_color=DANGER_COLOR,
            border_color=GRAY
        )

        # 字體
        self.title_font = None
        self.text_font = None
        self.small_font = None
        self.score_font = None


    def on_enter(self):
        """進入場景"""
        super().on_enter()
        self.title_font = pygame.font.SysFont("Microsoft JhengHei", 42)
        self.text_font = pygame.font.SysFont("Microsoft JhengHei", 24)
        self.small_font = pygame.font.SysFont("Microsoft JhengHei", 18)
        self.score_font = pygame.font.SysFont("Microsoft JhengHei", 48)

        # 預繪製增強版漸層背景（電漿青色調）
        self._bg_surface = self.create_enhanced_background(PLASMA_CYAN_DARK, add_vignette=True, add_grid=True)

        # 環境粒子（電漿粒子）
        self.ambient_particles = []
        for _ in range(25):
            self.ambient_particles.append({
                'x': random.randint(0, SCREEN_WIDTH),
                'y': random.randint(0, SCREEN_HEIGHT),
                'vx': random.uniform(-8, 8),
                'vy': random.uniform(-12, -3),
                'size': random.uniform(1, 2.5),
                'alpha': random.randint(15, 45)
            })

        # 重置狀態
        self.phase = self.PHASE_INSTRUCTIONS
        self.cursor_x = float(self.wafer_center_x)
        self.cursor_y = float(self.wafer_center_y)
        self.cursor_velocity_x = 0.0
        self.cursor_velocity_y = 0.0
        self.etching_elapsed = 0.0
        self.current_intensity = 0.0
        self.plasma_particles = []
        self.precision_score = 0

        # 生成目標圖案
        self._generate_target_pattern()

        # 重置蝕刻網格
        self.etched_grid = [[0.0] * self.GRID_SIZE for _ in range(self.GRID_SIZE)]

    def _generate_target_pattern(self):
        """生成 H 形電路圖案"""
        center = self.GRID_SIZE // 2
        half_width = 2   # 線條半寬度
        h_height = 12    # H 的高度範圍
        h_width = 10     # H 的寬度範圍

        # 清空網格
        for y in range(self.GRID_SIZE):
            for x in range(self.GRID_SIZE):
                self.target_grid[y][x] = False

        # H 的左側垂直線
        for y in range(center - h_height, center + h_height + 1):
            for x in range(center - h_width - half_width, center - h_width + half_width + 1):
                if self._is_in_wafer_grid(x, y):
                    self.target_grid[y][x] = True

        # H 的右側垂直線
        for y in range(center - h_height, center + h_height + 1):
            for x in range(center + h_width - half_width, center + h_width + half_width + 1):
                if self._is_in_wafer_grid(x, y):
                    self.target_grid[y][x] = True

        # H 的中間水平線
        for y in range(center - half_width, center + half_width + 1):
            for x in range(center - h_width, center + h_width + 1):
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

    def handle_event(self, event: pygame.event.Event):
        """處理事件"""
        if self.phase == self.PHASE_INSTRUCTIONS:
            self._handle_instructions_event(event)
        elif self.phase == self.PHASE_ETCHING:
            self._handle_etching_event(event)
        elif self.phase == self.PHASE_RESULT:
            self._handle_result_event(event)

        # ESC 返回選單
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.switch_to("menu")

    def _handle_instructions_event(self, event: pygame.event.Event):
        """指示階段事件處理"""
        if self.start_button.handle_event(event):
            self._start_etching()

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE or event.key == pygame.K_RETURN:
                self._start_etching()

    def _handle_etching_event(self, event: pygame.event.Event):
        """蝕刻階段事件處理"""
        pass  # 蝕刻期間不需要特別事件處理

    def _handle_result_event(self, event: pygame.event.Event):
        """結果階段事件處理"""
        if self.next_button.handle_event(event):
            self._finish_stage()

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE or event.key == pygame.K_RETURN:
                self._finish_stage()

    def _start_etching(self):
        """開始蝕刻階段"""
        self.phase = self.PHASE_ETCHING
        self.etching_elapsed = 0.0
        self.cursor_x = float(self.wafer_center_x)
        self.cursor_y = float(self.wafer_center_y)
        self.etched_grid = [[0.0] * self.GRID_SIZE for _ in range(self.GRID_SIZE)]
        self.plasma_particles = []

    def _finish_etching(self):
        """完成蝕刻，計算分數"""
        self.precision_score = self._calculate_precision_score()
        self.game.scores["precision"] = self.precision_score
        self.phase = self.PHASE_RESULT

    def _finish_stage(self):
        """完成關卡，進入結果畫面"""
        self.switch_to("result")

    def _get_cursor_velocity(self) -> tuple:
        """取得游標速度（根據陀螺儀，與 Stage 2 一致）"""
        if self.game.sensor and self.game.sensor.is_connected:
            data = self.game.sensor.get_imu_data()
            # 使用校正後的陀螺儀資料
            gx = data.gx  # 左右傾斜
            gy = data.gy  # 前後傾斜
        else:
            gx, gy = 0.0, 0.0

        def apply_deadzone_and_scale(gyro: float) -> float:
            if abs(gyro) < self.GYRO_DEADZONE:
                return 0.0

            sign = 1 if gyro > 0 else -1
            effective = abs(gyro) - self.GYRO_DEADZONE
            max_effective = self.GYRO_MAX - self.GYRO_DEADZONE
            effective = min(effective, max_effective)
            normalized = effective / max_effective
            speed = self.CURSOR_MIN_SPEED + normalized * (self.CURSOR_MAX_SPEED - self.CURSOR_MIN_SPEED)
            return sign * speed

        # gx 控制左右傾斜（取負號：左傾gx>0 → vx<0向左）
        vx = -apply_deadzone_and_scale(gx)
        # gy 控制前後傾斜
        vy = apply_deadzone_and_scale(gy)

        return (vx, vy)

    def _get_etch_intensity(self) -> float:
        """取得蝕刻強度（從搖晃）"""
        if self.game.sensor and self.game.sensor.is_connected:
            return self.game.sensor.get_shake_intensity()
        return 0.0

    def _update_cursor(self, dt: float):
        """更新游標位置"""
        vx, vy = self._get_cursor_velocity()

        # 平滑速度變化（與 Stage 2 一致）
        smoothing = 0.3
        self.cursor_velocity_x = self.cursor_velocity_x * (1 - smoothing) + vx * smoothing
        self.cursor_velocity_y = self.cursor_velocity_y * (1 - smoothing) + vy * smoothing

        # 更新位置
        self.cursor_x += self.cursor_velocity_x * dt
        self.cursor_y += self.cursor_velocity_y * dt

        # 限制在晶圓範圍內
        dx = self.cursor_x - self.wafer_center_x
        dy = self.cursor_y - self.wafer_center_y
        dist = math.sqrt(dx * dx + dy * dy)

        if dist > self.WAFER_RADIUS - 10:
            # 將游標推回晶圓內
            scale = (self.WAFER_RADIUS - 10) / dist
            self.cursor_x = self.wafer_center_x + dx * scale
            self.cursor_y = self.wafer_center_y + dy * scale

    def _cursor_to_grid(self, cx: float, cy: float) -> tuple:
        """將游標像素座標轉換為網格座標"""
        # 相對於晶圓中心的偏移
        dx = cx - self.wafer_center_x
        dy = cy - self.wafer_center_y

        # 轉換為網格座標（晶圓直徑對應整個網格）
        grid_center = self.GRID_SIZE // 2
        scale = self.GRID_SIZE / (self.WAFER_RADIUS * 2)

        gx = int(grid_center + dx * scale)
        gy = int(grid_center + dy * scale)

        return (gx, gy)

    def _grid_to_pixel(self, gx: int, gy: int) -> tuple:
        """將網格座標轉換為像素座標"""
        grid_center = self.GRID_SIZE // 2
        scale = (self.WAFER_RADIUS * 2) / self.GRID_SIZE

        px = self.wafer_center_x + (gx - grid_center) * scale
        py = self.wafer_center_y + (gy - grid_center) * scale

        return (px, py)

    def _etch_at_cursor(self, intensity: float, dt: float):
        """在游標位置進行蝕刻"""
        if intensity <= 0:
            return

        # 取得網格座標
        gx, gy = self._cursor_to_grid(self.cursor_x, self.cursor_y)

        # 計算蝕刻量和筆刷大小
        etch_amount = (self.ETCH_RATE_BASE + intensity * (self.ETCH_RATE_MAX - self.ETCH_RATE_BASE)) * dt
        brush_radius = self.BRUSH_RADIUS_BASE + int(intensity * (self.BRUSH_RADIUS_MAX - self.BRUSH_RADIUS_BASE))

        # 在筆刷範圍內蝕刻
        for dx in range(-brush_radius, brush_radius + 1):
            for dy in range(-brush_radius, brush_radius + 1):
                nx, ny = gx + dx, gy + dy
                if self._is_in_wafer_grid(nx, ny):
                    # 距離衰減
                    dist = math.sqrt(dx * dx + dy * dy)
                    if dist <= brush_radius:
                        falloff = 1.0 - (dist / (brush_radius + 1))
                        self.etched_grid[ny][nx] = min(1.0, self.etched_grid[ny][nx] + etch_amount * falloff)

    def _spawn_plasma_particles(self, intensity: float):
        """生成電漿粒子效果"""
        if intensity <= 0 or random.random() > intensity:
            return

        count = int(1 + intensity * 3)
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(30, 80) * intensity
            self.plasma_particles.append({
                "x": self.cursor_x,
                "y": self.cursor_y,
                "vx": math.cos(angle) * speed,
                "vy": math.sin(angle) * speed,
                "life": 0.5,
                "max_life": 0.5,
            })

    def _update_particles(self, dt: float):
        """更新粒子"""
        for p in self.plasma_particles[:]:
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["life"] -= dt

            if p["life"] <= 0:
                self.plasma_particles.remove(p)

    def _calculate_precision_score(self) -> int:
        """計算蝕刻精準度分數"""
        target_count = 0
        etched_on_target = 0
        etched_off_target = 0
        etch_depths = []

        for y in range(self.GRID_SIZE):
            for x in range(self.GRID_SIZE):
                if not self._is_in_wafer_grid(x, y):
                    continue

                is_target = self.target_grid[y][x]
                etch_depth = self.etched_grid[y][x]

                if is_target:
                    target_count += 1
                    if etch_depth > 0.3:  # 視為已蝕刻
                        etched_on_target += 1
                        etch_depths.append(etch_depth)
                else:
                    if etch_depth > 0.3:  # 過度蝕刻
                        etched_off_target += 1

        # 覆蓋率 (40%)：目標區域被蝕刻的比例
        if target_count > 0:
            coverage = etched_on_target / target_count
        else:
            coverage = 0.0

        # 準確率 (40%)：正確蝕刻 vs 總蝕刻
        total_etched = etched_on_target + etched_off_target
        if total_etched > 0:
            accuracy = etched_on_target / total_etched
        else:
            accuracy = 0.0

        # 均勻度 (20%)：蝕刻深度一致性
        if len(etch_depths) > 1:
            avg_depth = sum(etch_depths) / len(etch_depths)
            variance = sum((d - avg_depth) ** 2 for d in etch_depths) / len(etch_depths)
            std_dev = variance ** 0.5
            uniformity = max(0.0, 1.0 - std_dev)
        else:
            uniformity = 0.5

        # 儲存分項分數
        self.coverage_score = int(coverage * 100)
        self.accuracy_score = int(accuracy * 100)
        self.uniformity_score = int(uniformity * 100)

        # 加權總分
        COVERAGE_WEIGHT = 0.40
        ACCURACY_WEIGHT = 0.40
        UNIFORMITY_WEIGHT = 0.20

        score = (
            coverage * COVERAGE_WEIGHT +
            accuracy * ACCURACY_WEIGHT +
            uniformity * UNIFORMITY_WEIGHT
        ) * 100

        return int(max(0, min(100, score)))

    def update(self, dt: float):
        """更新遊戲邏輯"""
        # 更新淡入淡出
        self.update_fade(dt)

        # 更新動畫
        self.pulse_animation += dt * 5

        # 更新按鈕動畫
        self.start_button.update(dt)
        self.next_button.update(dt)

        # 更新進度條動畫
        self.timer_bar.update(dt)
        self.intensity_bar.update(dt)

        # 更新環境粒子
        self._update_ambient_particles(dt)

        if self.phase == self.PHASE_INSTRUCTIONS:
            pass
        elif self.phase == self.PHASE_ETCHING:
            self._update_etching_phase(dt)
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

    def _update_etching_phase(self, dt: float):
        """蝕刻階段更新"""
        # 更新計時
        self.etching_elapsed += dt
        remaining = max(0, self.ETCHING_DURATION - self.etching_elapsed)
        self.timer_bar.set_progress(remaining / self.ETCHING_DURATION)

        # 更新游標
        self._update_cursor(dt)

        # 取得蝕刻強度
        self.current_intensity = self._get_etch_intensity()
        self.intensity_bar.set_progress(self.current_intensity)

        # 蝕刻
        self._etch_at_cursor(self.current_intensity, dt)

        # 生成粒子
        self._spawn_plasma_particles(self.current_intensity)
        self._update_particles(dt)

        # 更新游標發光效果
        if self.current_intensity > 0:
            self.cursor_glow = min(1.0, self.cursor_glow + dt * 5)
        else:
            self.cursor_glow = max(0.0, self.cursor_glow - dt * 3)

        # 檢查時間結束
        if self.etching_elapsed >= self.ETCHING_DURATION:
            self._finish_etching()

    def draw(self, screen: pygame.Surface):
        """繪製場景"""
        self._draw_background(screen)

        # 環境粒子
        self._draw_ambient_particles(screen)

        if self.phase == self.PHASE_INSTRUCTIONS:
            self._draw_instructions(screen)
        elif self.phase == self.PHASE_ETCHING:
            self._draw_etching_phase(screen)
        elif self.phase == self.PHASE_RESULT:
            self._draw_result(screen)

        # 淡入淡出遮罩
        self.draw_fade_overlay(screen)

    def _draw_ambient_particles(self, screen: pygame.Surface):
        """繪製環境粒子"""
        for p in self.ambient_particles:
            surf = pygame.Surface((int(p['size'] * 2), int(p['size'] * 2)), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*PLASMA_CYAN, p['alpha']),
                             (int(p['size']), int(p['size'])), int(p['size']))
            screen.blit(surf, (int(p['x'] - p['size']), int(p['y'] - p['size'])))

    def _draw_background(self, screen: pygame.Surface):
        """繪製漸層背景（使用預繪製的快取）"""
        screen.blit(self._bg_surface, (0, 0))

    def _draw_instructions(self, screen: pygame.Surface):
        """繪製指示畫面"""
        # 標題（帶光暈）
        self.draw_title(screen, "蝕刻 - 精準控制", y=50, font=self.title_font)

        # 晶圓預覽（含目標圖案）
        self._draw_wafer(screen, show_target=True, show_etched=False)

        # 說明文字
        instructions = [
            "傾斜裝置移動蝕刻光束",
            "搖晃裝置進行蝕刻",
            "沿著紫色圖案進行蝕刻！"
        ]

        y_start = 480
        for i, text in enumerate(instructions):
            surface = self.text_font.render(text, True, TEXT_SECONDARY)
            rect = surface.get_rect(center=(SCREEN_WIDTH // 2, y_start + i * 30))
            screen.blit(surface, rect)

        # 開始按鈕
        self.start_button.draw(screen)

    def _draw_etching_phase(self, screen: pygame.Surface):
        """繪製蝕刻階段"""
        # 標題
        title = self.title_font.render("蝕刻中！", True, WHITE)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 40))
        screen.blit(title, title_rect)

        # 計時器
        remaining = max(0, self.ETCHING_DURATION - self.etching_elapsed)
        timer_text = f"剩餘時間: {remaining:.1f}s"
        timer_surface = self.text_font.render(timer_text, True, WHITE)
        timer_rect = timer_surface.get_rect(center=(SCREEN_WIDTH // 2, 100))
        screen.blit(timer_surface, timer_rect)
        self.timer_bar.draw(screen)

        # 晶圓（含目標和蝕刻進度）
        self._draw_wafer(screen, show_target=True, show_etched=True)

        # 游標
        self._draw_cursor(screen)

        # 粒子
        self._draw_particles(screen)

        # 蝕刻強度
        intensity_label = f"蝕刻強度: {int(self.current_intensity * 100)}%"
        intensity_surface = self.small_font.render(intensity_label, True, WHITE)
        intensity_rect = intensity_surface.get_rect(center=(SCREEN_WIDTH // 2, 525))
        screen.blit(intensity_surface, intensity_rect)
        self.intensity_bar.draw(screen)

        # 即時統計
        coverage, accuracy = self._get_realtime_stats()
        stats_text = f"覆蓋率: {coverage}%  |  準確率: {accuracy}%"
        stats_surface = self.small_font.render(stats_text, True, LIGHT_GRAY)
        stats_rect = stats_surface.get_rect(center=(SCREEN_WIDTH // 2, 580))
        screen.blit(stats_surface, stats_rect)

        # 提示
        hint = "傾斜移動 + 搖晃蝕刻"
        hint_surface = self.small_font.render(hint, True, GRAY)
        hint_rect = hint_surface.get_rect(center=(SCREEN_WIDTH // 2, 650))
        screen.blit(hint_surface, hint_rect)

    def _draw_result(self, screen: pygame.Surface):
        """繪製結果畫面"""
        # 標題
        title = self.title_font.render("蝕刻完成！", True, WHITE)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 50))
        screen.blit(title, title_rect)

        # 完成的晶圓
        self._draw_wafer(screen, show_target=False, show_etched=True)

        # 分數顯示
        score_color = SECONDARY_COLOR if self.precision_score >= 70 else ACCENT_COLOR if self.precision_score >= 40 else DANGER_COLOR
        score_text = f"精準度: {self.precision_score} 分"
        score_surface = self.score_font.render(score_text, True, score_color)
        score_rect = score_surface.get_rect(center=(SCREEN_WIDTH // 2, 480))
        screen.blit(score_surface, score_rect)

        # 詳細分數
        details = [
            f"覆蓋率: {self.coverage_score}%",
            f"準確率: {self.accuracy_score}%",
            f"均勻度: {self.uniformity_score}%"
        ]

        y_start = 530
        for i, text in enumerate(details):
            surface = self.small_font.render(text, True, LIGHT_GRAY)
            rect = surface.get_rect(center=(SCREEN_WIDTH // 2, y_start + i * 25))
            screen.blit(surface, rect)

        # 繼續按鈕
        self.next_button.draw(screen)

    def _draw_wafer(self, screen: pygame.Surface, show_target: bool, show_etched: bool):
        """繪製晶圓"""
        cx, cy = self.wafer_center_x, self.wafer_center_y
        radius = self.WAFER_RADIUS

        # 晶圓底座
        pygame.draw.circle(screen, DARK_GRAY, (cx, cy), radius + 5)

        # 晶圓本體
        pygame.draw.circle(screen, SILICON_BLUE, (cx, cy), radius)

        # 繪製網格內容
        cell_size = (radius * 2) / self.GRID_SIZE

        for gy in range(self.GRID_SIZE):
            for gx in range(self.GRID_SIZE):
                if not self._is_in_wafer_grid(gx, gy):
                    continue

                px, py = self._grid_to_pixel(gx, gy)
                is_target = self.target_grid[gy][gx]
                etch_depth = self.etched_grid[gy][gx]

                # 顯示目標圖案
                if show_target and is_target and (not show_etched or etch_depth < 0.3):
                    surf = pygame.Surface((cell_size + 1, cell_size + 1), pygame.SRCALPHA)
                    surf.fill((*PHOTORESIST_PURPLE, 150))
                    screen.blit(surf, (px - cell_size / 2, py - cell_size / 2))

                # 顯示已蝕刻區域
                if show_etched and etch_depth > 0.1:
                    if is_target:
                        # 正確蝕刻 - 深色
                        alpha = int(200 * etch_depth)
                        color = (30, 60, 100, alpha)
                    else:
                        # 過度蝕刻 - 紅色警告
                        alpha = int(180 * etch_depth)
                        color = (*DANGER_COLOR, alpha)

                    surf = pygame.Surface((cell_size + 1, cell_size + 1), pygame.SRCALPHA)
                    surf.fill(color)
                    screen.blit(surf, (px - cell_size / 2, py - cell_size / 2))

        # 邊框
        pygame.draw.circle(screen, WHITE, (cx, cy), radius, 2)

    def _draw_cursor(self, screen: pygame.Surface):
        """繪製蝕刻游標"""
        cx, cy = int(self.cursor_x), int(self.cursor_y)

        # 發光效果
        if self.cursor_glow > 0:
            glow_radius = int(20 + self.cursor_glow * 15)
            for i in range(5, 0, -1):
                alpha = int(30 * self.cursor_glow * (6 - i) / 5)
                r = glow_radius + i * 5
                surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
                pygame.draw.circle(surf, (*ACCENT_COLOR, alpha), (r, r), r)
                screen.blit(surf, (cx - r, cy - r))

        # 游標核心
        pulse = 0.8 + 0.2 * math.sin(self.pulse_animation)
        core_radius = int(8 * pulse)

        if self.current_intensity > 0:
            # 蝕刻中 - 亮黃色
            pygame.draw.circle(screen, ACCENT_COLOR, (cx, cy), core_radius + 2)
            pygame.draw.circle(screen, WHITE, (cx, cy), core_radius)
        else:
            # 待機 - 藍色
            pygame.draw.circle(screen, PRIMARY_COLOR, (cx, cy), core_radius + 2)
            pygame.draw.circle(screen, LIGHT_GRAY, (cx, cy), core_radius)

        # 方向指示
        vx, vy = self._get_cursor_velocity()
        if abs(vx) > 10 or abs(vy) > 10:
            length = 25
            mag = math.sqrt(vx * vx + vy * vy)
            if mag > 0:
                end_x = cx + int((vx / mag) * length)
                end_y = cy + int((vy / mag) * length)
                pygame.draw.line(screen, WHITE, (cx, cy), (end_x, end_y), 2)

    def _draw_particles(self, screen: pygame.Surface):
        """繪製電漿粒子"""
        for p in self.plasma_particles:
            alpha = int(255 * (p["life"] / p["max_life"]))
            size = int(3 * (p["life"] / p["max_life"]))
            if size > 0:
                surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
                color = (*ACCENT_COLOR, alpha)
                pygame.draw.circle(surf, color, (size, size), size)
                screen.blit(surf, (int(p["x"]) - size, int(p["y"]) - size))

    def _get_realtime_stats(self) -> tuple:
        """取得即時統計"""
        target_count = 0
        etched_on_target = 0
        etched_off_target = 0

        for y in range(self.GRID_SIZE):
            for x in range(self.GRID_SIZE):
                if not self._is_in_wafer_grid(x, y):
                    continue

                is_target = self.target_grid[y][x]
                etch_depth = self.etched_grid[y][x]

                if is_target:
                    target_count += 1
                    if etch_depth > 0.3:
                        etched_on_target += 1
                else:
                    if etch_depth > 0.3:
                        etched_off_target += 1

        coverage = int(100 * etched_on_target / target_count) if target_count > 0 else 0
        total_etched = etched_on_target + etched_off_target
        accuracy = int(100 * etched_on_target / total_etched) if total_etched > 0 else 100

        return coverage, accuracy
