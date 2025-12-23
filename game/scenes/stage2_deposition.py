"""
第二關：薄膜沉積
玩家傾斜感測器控制游標方向與速度，在畫面上畫出圓形，
最後比對使用者畫出的圓形與標準圓形的相似度
"""

import pygame
import math
import random
from .base import Scene, Button, ProgressBar
from ..config import *
from ..utils.cv_scoring import CircleSimilarityScorer


class DepositionStage(Scene):
    """薄膜沉積關卡 - 傾斜畫圓"""

    # 遊戲階段
    PHASE_INSTRUCTIONS = 0
    PHASE_DRAWING = 1
    PHASE_RESULT = 2

    # 陀螺儀參數（用於傾斜判斷）
    GYRO_DEADZONE = 300           # 死區（濾除平放時的雜訊）
    GYRO_MAX = 2000               # 最大有效值
    CURSOR_MAX_SPEED = 300.0      # 最大移動速度（像素/秒）
    CURSOR_MIN_SPEED = 50.0       # 最小移動速度（像素/秒）

    # 圓形參數
    TARGET_RADIUS = 150           # 目標圓半徑（像素）
    TRAIL_POINT_INTERVAL = 5      # 軌跡點間隔（像素）
    MIN_POINTS_FOR_SCORE = 20     # 最小計分點數

    def __init__(self, game):
        super().__init__(game)

        # 遊戲階段
        self.phase = self.PHASE_INSTRUCTIONS

        # 游標狀態
        self.cursor_x = SCREEN_WIDTH // 2
        self.cursor_y = SCREEN_HEIGHT // 2
        self.cursor_velocity_x = 0.0
        self.cursor_velocity_y = 0.0

        # 目標圓（畫面中央）
        self.target_center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        self.target_radius = self.TARGET_RADIUS

        # 繪製狀態
        self.is_drawing = False
        self.drawn_points = []
        self.last_recorded_pos = None

        # 分數
        self.similarity_score = 0
        self.distance_score = 0
        self.circularity_score = 0
        self.completeness_score = 0

        # 動畫
        self.spray_particles = []
        self.dash_offset = 0

        # OpenCV 評分器
        self.cv_scorer = None

        # 計時器
        self.drawing_time_limit = 20.0  # 20 秒限時
        self.drawing_elapsed = 0.0

        # UI 元件
        center_x = SCREEN_WIDTH // 2
        self.start_button = Button(
            center_x - 100, 550, 200, 50,
            "開始繪製", PRIMARY_COLOR
        )
        self.next_button = Button(
            center_x - 100, 620, 200, 50,
            "繼續", PRIMARY_COLOR
        )
        self.progress_bar = ProgressBar(
            center_x - 250, 650, 500, 25,
            bg_color=DARK_GRAY,
            fill_color=SECONDARY_COLOR,
            border_color=GRAY
        )
        self.timer_bar = ProgressBar(
            center_x - 200, 70, 400, 20,
            bg_color=DARK_GRAY,
            fill_color=ACCENT_COLOR,
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

        # 預繪製增強版漸層背景
        self._bg_surface = self.create_enhanced_background(SILICON_BLUE, add_vignette=True, add_grid=False)

        # 初始化環境粒子
        self.ambient_particles = []
        for _ in range(25):
            self.ambient_particles.append({
                'x': random.randint(0, SCREEN_WIDTH),
                'y': random.randint(0, SCREEN_HEIGHT),
                'vx': random.uniform(-8, 8),
                'vy': random.uniform(-15, -3),
                'size': random.uniform(1, 2.5),
                'alpha': random.randint(15, 40)
            })

        # 重置狀態
        self.phase = self.PHASE_INSTRUCTIONS
        self.cursor_x = SCREEN_WIDTH // 2
        self.cursor_y = SCREEN_HEIGHT // 2
        self.cursor_velocity_x = 0.0
        self.cursor_velocity_y = 0.0
        self.is_drawing = False
        self.drawn_points = []
        self.last_recorded_pos = None
        self.similarity_score = 0
        self.spray_particles = []
        self.drawing_elapsed = 0.0

        # 動畫狀態
        self.glow_phase = 0.0

        # 初始化 OpenCV 評分器
        self.cv_scorer = CircleSimilarityScorer(
            canvas_size=(SCREEN_WIDTH, SCREEN_HEIGHT),
            target_center=self.target_center,
            target_radius=self.target_radius,
        )

    def handle_event(self, event: pygame.event.Event):
        """處理事件"""
        if self.phase == self.PHASE_INSTRUCTIONS:
            self._handle_instructions_event(event)
        elif self.phase == self.PHASE_DRAWING:
            self._handle_drawing_event(event)
        elif self.phase == self.PHASE_RESULT:
            self._handle_result_event(event)

        # ESC 返回選單
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.switch_to("menu")

    def _handle_instructions_event(self, event: pygame.event.Event):
        """指示階段事件處理"""
        if self.start_button.handle_event(event):
            self._start_drawing()

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE or event.key == pygame.K_RETURN:
                self._start_drawing()

    def _handle_drawing_event(self, event: pygame.event.Event):
        """繪製階段事件處理"""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                self._finish_drawing()
            elif event.key == pygame.K_r:
                # 重置繪製
                self.drawn_points = []
                self.last_recorded_pos = None

    def _handle_result_event(self, event: pygame.event.Event):
        """結果階段事件處理"""
        if self.next_button.handle_event(event):
            self._finish_stage()

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE or event.key == pygame.K_RETURN:
                self._finish_stage()

    def _start_drawing(self):
        """開始繪製階段"""
        self.phase = self.PHASE_DRAWING
        self.is_drawing = True
        self.drawn_points = []
        self.last_recorded_pos = None
        self.drawing_elapsed = 0.0

        # 游標起始位置（目標圓右側）
        self.cursor_x = self.target_center[0] + self.target_radius
        self.cursor_y = self.target_center[1]

    def _finish_drawing(self):
        """完成繪製，進入結果階段"""
        self.is_drawing = False
        self.similarity_score = self._calculate_similarity_score()
        self.game.scores["uniformity"] = self.similarity_score
        self.phase = self.PHASE_RESULT

    def _finish_stage(self):
        """完成關卡，進入下一關"""
        self.switch_to("stage3")

    def update(self, dt: float):
        """更新遊戲邏輯"""
        # 更新淡入淡出
        self.update_fade(dt)

        # 更新動畫
        self.dash_offset += dt * 50
        self.glow_phase += dt * 3

        # 更新按鈕動畫
        self.start_button.update(dt)
        self.next_button.update(dt)

        # 更新進度條動畫
        self.progress_bar.update(dt)
        self.timer_bar.update(dt)

        # 更新環境粒子
        self._update_ambient_particles(dt)

        if self.phase == self.PHASE_INSTRUCTIONS:
            pass  # 等待使用者開始
        elif self.phase == self.PHASE_DRAWING:
            self._update_drawing_phase(dt)
        elif self.phase == self.PHASE_RESULT:
            self._update_result_phase(dt)

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

    def _update_drawing_phase(self, dt: float):
        """繪製階段更新"""
        # 更新計時器
        self.drawing_elapsed += dt
        remaining = max(0, self.drawing_time_limit - self.drawing_elapsed)
        self.timer_bar.set_progress(remaining / self.drawing_time_limit)

        # 時間到自動完成
        if self.drawing_elapsed >= self.drawing_time_limit:
            self._finish_drawing()
            return

        # 更新游標
        self._update_cursor(dt)

        # 記錄軌跡
        if self.is_drawing:
            self._record_trail_point()

        # 更新噴灑粒子
        self._update_spray_particles(dt)

    def _update_result_phase(self, dt: float):
        """結果階段更新"""
        pass

    def _get_cursor_velocity(self) -> tuple:
        """取得游標速度（根據陀螺儀）"""
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

    def _update_cursor(self, dt: float):
        """更新游標位置"""
        vx, vy = self._get_cursor_velocity()

        # 平滑速度變化
        smoothing = 0.3
        self.cursor_velocity_x = self.cursor_velocity_x * (1 - smoothing) + vx * smoothing
        self.cursor_velocity_y = self.cursor_velocity_y * (1 - smoothing) + vy * smoothing

        # 更新位置
        self.cursor_x += self.cursor_velocity_x * dt
        self.cursor_y += self.cursor_velocity_y * dt

        # 限制在畫面範圍內
        padding = 50
        self.cursor_x = max(padding, min(SCREEN_WIDTH - padding, self.cursor_x))
        self.cursor_y = max(padding, min(SCREEN_HEIGHT - padding, self.cursor_y))

    def _record_trail_point(self):
        """記錄軌跡點"""
        current_pos = (int(self.cursor_x), int(self.cursor_y))

        if self.last_recorded_pos is None:
            self.drawn_points.append(current_pos)
            self.last_recorded_pos = current_pos
            return

        dx = current_pos[0] - self.last_recorded_pos[0]
        dy = current_pos[1] - self.last_recorded_pos[1]
        distance = math.sqrt(dx * dx + dy * dy)

        if distance >= self.TRAIL_POINT_INTERVAL:
            self.drawn_points.append(current_pos)
            self.last_recorded_pos = current_pos

    def _update_spray_particles(self, dt: float):
        """更新噴灑粒子效果"""
        import random

        # 移除死亡粒子
        self.spray_particles = [p for p in self.spray_particles if p['life'] > 0]

        # 新增粒子
        if self.is_drawing and len(self.spray_particles) < 15:
            speed = math.sqrt(self.cursor_velocity_x**2 + self.cursor_velocity_y**2)
            if speed > 10:
                for _ in range(2):
                    self.spray_particles.append({
                        'x': self.cursor_x + random.uniform(-8, 8),
                        'y': self.cursor_y + random.uniform(-8, 8),
                        'vx': random.uniform(-30, 30),
                        'vy': random.uniform(-30, 30),
                        'life': 1.0,
                        'size': random.uniform(3, 6)
                    })

        # 更新粒子
        for p in self.spray_particles:
            p['x'] += p['vx'] * dt
            p['y'] += p['vy'] * dt
            p['life'] -= dt * 3

    # ==================== 分數計算 ====================

    def _calculate_similarity_score(self) -> int:
        """使用 OpenCV 計算總相似度分數"""
        if len(self.drawn_points) < self.MIN_POINTS_FOR_SCORE:
            self.distance_score = 0
            self.circularity_score = 0
            self.completeness_score = 0
            return 0

        # 使用 OpenCV 評分器
        total_score, component_scores = self.cv_scorer.get_combined_score(
            self.drawn_points
        )

        # 將 OpenCV 分數映射到原有的顯示欄位
        # distance_score -> 位置準確度 (center_distance)
        # circularity_score -> 圓度 (circularity)
        # completeness_score -> 形狀匹配 (hu_moment)
        self.distance_score = component_scores["center_distance"]
        self.circularity_score = component_scores["circularity"]
        self.completeness_score = component_scores["hu_moment"]

        return total_score

    def _calculate_distance_score(self) -> float:
        """計算距離分數：點與理想圓周的接近程度"""
        if len(self.drawn_points) < self.MIN_POINTS_FOR_SCORE:
            return 0.0

        cx, cy = self.target_center
        r = self.target_radius

        total_error = 0.0
        for px, py in self.drawn_points:
            dist_to_center = math.sqrt((px - cx)**2 + (py - cy)**2)
            error = abs(dist_to_center - r)
            total_error += error

        # 防止除以零
        if not self.drawn_points:
            return 0.0
        avg_error = total_error / len(self.drawn_points)
        max_acceptable_error = r / 2
        score = max(0, 100 * (1 - avg_error / max_acceptable_error))

        return score

    def _calculate_circularity_score(self) -> float:
        """計算圓度分數：形狀的圓形程度"""
        if len(self.drawn_points) < self.MIN_POINTS_FOR_SCORE:
            return 0.0

        # 計算繪製點的質心
        avg_x = sum(p[0] for p in self.drawn_points) / len(self.drawn_points)
        avg_y = sum(p[1] for p in self.drawn_points) / len(self.drawn_points)

        # 計算各點到質心的距離（半徑）
        radii = []
        for px, py in self.drawn_points:
            r = math.sqrt((px - avg_x)**2 + (py - avg_y)**2)
            radii.append(r)

        if not radii:
            return 0.0

        mean_radius = sum(radii) / len(radii)
        if mean_radius == 0:
            return 0.0

        variance = sum((r - mean_radius)**2 for r in radii) / len(radii)
        std_dev = math.sqrt(variance)

        # 變異係數（越小越圓）
        cv = std_dev / mean_radius
        score = max(0, 100 * (1 - cv / 0.5))

        return score

    def _calculate_completeness_score(self) -> float:
        """計算完整度分數：圓周覆蓋率"""
        if len(self.drawn_points) < self.MIN_POINTS_FOR_SCORE:
            return 0.0

        cx, cy = self.target_center

        # 將圓分成 36 個扇區（每個 10 度）
        num_sectors = 36
        sector_covered = [False] * num_sectors

        for px, py in self.drawn_points:
            dx = px - cx
            dy = py - cy
            angle = math.atan2(dy, dx)
            angle_deg = math.degrees(angle)
            if angle_deg < 0:
                angle_deg += 360

            sector_idx = int(angle_deg / (360 / num_sectors)) % num_sectors
            sector_covered[sector_idx] = True

        coverage = sum(sector_covered) / num_sectors * 100
        return coverage

    # ==================== 繪製 ====================

    def draw(self, screen: pygame.Surface):
        """繪製場景"""
        self._draw_background(screen)

        # 環境粒子
        self._draw_ambient_particles(screen)

        if self.phase == self.PHASE_INSTRUCTIONS:
            self._draw_instructions(screen)
        elif self.phase == self.PHASE_DRAWING:
            self._draw_drawing_phase(screen)
        elif self.phase == self.PHASE_RESULT:
            self._draw_result(screen)

        # 淡入淡出遮罩
        self.draw_fade_overlay(screen)

    def _draw_ambient_particles(self, screen: pygame.Surface):
        """繪製環境粒子"""
        for p in self.ambient_particles:
            surf = pygame.Surface((int(p['size'] * 2), int(p['size'] * 2)), pygame.SRCALPHA)
            pygame.draw.circle(surf, (200, 220, 255, p['alpha']),
                             (int(p['size']), int(p['size'])), int(p['size']))
            screen.blit(surf, (int(p['x'] - p['size']), int(p['y'] - p['size'])))

    def _draw_background(self, screen: pygame.Surface):
        """繪製漸層背景（使用預繪製的快取）"""
        screen.blit(self._bg_surface, (0, 0))

    def _draw_instructions(self, screen: pygame.Surface):
        """繪製指示畫面"""
        # 標題（帶光暈）
        self.draw_title(screen, "薄膜沉積 - 畫出圓形", y=80, font=self.title_font)

        # 目標圓（預覽）
        self._draw_target_circle(screen)

        # 說明文字
        instructions = [
            "傾斜裝置來控制游標方向與速度",
            "沿著虛線圓圈畫出一個圓形",
            "畫得越圓、越接近目標，分數越高！"
        ]

        y_start = 450
        for i, text in enumerate(instructions):
            surface = self.text_font.render(text, True, TEXT_SECONDARY)
            rect = surface.get_rect(center=(SCREEN_WIDTH // 2, y_start + i * 35))
            screen.blit(surface, rect)

        # 開始按鈕
        self.start_button.draw(screen)

    def _draw_drawing_phase(self, screen: pygame.Surface):
        """繪製繪畫階段"""
        # 標題（帶光暈）
        self.draw_title(screen, "薄膜沉積 - 畫出圓形", y=40, font=self.title_font)

        # 計時器
        self.timer_bar.draw(screen)
        remaining = max(0, self.drawing_time_limit - self.drawing_elapsed)
        if remaining < 5:
            timer_color = DANGER_COLOR
        elif remaining < 10:
            timer_color = ACCENT_COLOR
        else:
            timer_color = TEXT_HIGHLIGHT
        timer_text = f"剩餘時間: {remaining:.1f}s"
        timer_surface = self.text_font.render(timer_text, True, timer_color)
        timer_rect = timer_surface.get_rect(center=(SCREEN_WIDTH // 2, 100))
        screen.blit(timer_surface, timer_rect)

        # 目標圓
        self._draw_target_circle(screen)

        # 繪製軌跡
        self._draw_trail(screen)

        # 繪製游標
        self._draw_cursor(screen)

        # 繪製噴灑粒子
        self._draw_spray_particles(screen)

        # 提示文字
        hint = "傾斜裝置移動游標！"
        hint_surface = self.text_font.render(hint, True, TEXT_SECONDARY)
        hint_rect = hint_surface.get_rect(center=(SCREEN_WIDTH // 2, 620))
        screen.blit(hint_surface, hint_rect)

        # 完成提示
        finish_hint = "按 R 重置 | 時間到自動完成"
        finish_surface = self.small_font.render(finish_hint, True, ACCENT_COLOR)
        finish_rect = finish_surface.get_rect(center=(SCREEN_WIDTH // 2, 660))
        screen.blit(finish_surface, finish_rect)

        # 點數顯示（帶背景面板）
        points_text = f"軌跡點數: {len(self.drawn_points)}"
        points_surface = self.small_font.render(points_text, True, TEXT_SECONDARY)
        # 背景
        bg_rect = points_surface.get_rect(topleft=(20, 20)).inflate(16, 8)
        bg_surf = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(bg_surf, (*BG_DARK, 180), (0, 0, bg_rect.width, bg_rect.height), border_radius=5)
        screen.blit(bg_surf, bg_rect.topleft)
        screen.blit(points_surface, (28, 24))

    def _draw_result(self, screen: pygame.Surface):
        """繪製結果畫面"""
        # 標題
        title = self.title_font.render("繪製完成！", True, WHITE)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 50))
        screen.blit(title, title_rect)

        # 比較區域
        compare_y = 280

        # 左側：目標圓
        left_x = SCREEN_WIDTH // 3
        pygame.draw.circle(screen, LIGHT_GRAY, (left_x, compare_y), self.target_radius, 3)
        label1 = self.text_font.render("目標圓形", True, WHITE)
        label1_rect = label1.get_rect(center=(left_x, compare_y + self.target_radius + 30))
        screen.blit(label1, label1_rect)

        # 右側：使用者繪製
        right_x = 2 * SCREEN_WIDTH // 3
        if len(self.drawn_points) >= 2:
            # 計算偏移量使繪製居中
            offset_x = right_x - self.target_center[0]
            shifted_points = [(p[0] + offset_x, p[1]) for p in self.drawn_points]
            pygame.draw.lines(screen, PRIMARY_COLOR, False, shifted_points, 4)

        label2 = self.text_font.render("你的繪製", True, WHITE)
        label2_rect = label2.get_rect(center=(right_x, compare_y + self.target_radius + 30))
        screen.blit(label2, label2_rect)

        # 分數顯示
        score_y = 500

        # 總分
        score_color = SECONDARY_COLOR if self.similarity_score >= 70 else ACCENT_COLOR if self.similarity_score >= 40 else DANGER_COLOR
        score_text = f"相似度: {self.similarity_score} 分"
        score_surface = self.score_font.render(score_text, True, score_color)
        score_rect = score_surface.get_rect(center=(SCREEN_WIDTH // 2, score_y))
        screen.blit(score_surface, score_rect)

        # 細項分數
        detail_y = score_y + 50
        details = [
            f"距離分數: {int(self.distance_score)}",
            f"圓度分數: {int(self.circularity_score)}",
            f"完整度: {int(self.completeness_score)}",
        ]

        detail_text = "  |  ".join(details)
        detail_surface = self.small_font.render(detail_text, True, LIGHT_GRAY)
        detail_rect = detail_surface.get_rect(center=(SCREEN_WIDTH // 2, detail_y))
        screen.blit(detail_surface, detail_rect)

        # 繼續按鈕
        self.next_button.draw(screen)

    def _draw_target_circle(self, screen: pygame.Surface):
        """繪製目標圓（虛線）"""
        cx, cy = self.target_center
        r = self.target_radius

        # 虛線圓
        num_dashes = 36
        dash_angle = 2 * math.pi / num_dashes

        for i in range(num_dashes):
            if i % 2 == 0:
                start_angle = i * dash_angle + self.dash_offset * 0.02
                end_angle = start_angle + dash_angle * 0.7

                start_x = cx + r * math.cos(start_angle)
                start_y = cy + r * math.sin(start_angle)
                end_x = cx + r * math.cos(end_angle)
                end_y = cy + r * math.sin(end_angle)

                pygame.draw.line(screen, LIGHT_GRAY, (start_x, start_y), (end_x, end_y), 2)

        # 中心十字
        cross_size = 15
        pygame.draw.line(screen, GRAY, (cx - cross_size, cy), (cx + cross_size, cy), 1)
        pygame.draw.line(screen, GRAY, (cx, cy - cross_size), (cx, cy + cross_size), 1)

    def _draw_cursor(self, screen: pygame.Surface):
        """繪製游標（沉積噴頭）"""
        x, y = int(self.cursor_x), int(self.cursor_y)

        # 噴頭外圈
        pygame.draw.circle(screen, POLYSILICON_GRAY, (x, y), 15)
        pygame.draw.circle(screen, WHITE, (x, y), 15, 2)

        # 噴頭內圈（根據速度變色）
        speed = math.sqrt(self.cursor_velocity_x**2 + self.cursor_velocity_y**2)
        inner_color = SECONDARY_COLOR if speed > 50 else PRIMARY_COLOR
        pygame.draw.circle(screen, inner_color, (x, y), 8)

        # 方向指示
        if speed > 20:
            dir_x = self.cursor_velocity_x / max(speed, 1) * 25
            dir_y = self.cursor_velocity_y / max(speed, 1) * 25
            pygame.draw.line(screen, ACCENT_COLOR, (x, y), (x + dir_x, y + dir_y), 3)

    def _draw_trail(self, screen: pygame.Surface):
        """繪製沉積軌跡"""
        if len(self.drawn_points) < 2:
            return

        # 軌跡線
        pygame.draw.lines(screen, PRIMARY_COLOR, False, self.drawn_points, 6)

        # 軌跡點標記
        for i, point in enumerate(self.drawn_points):
            if i % 10 == 0:
                pygame.draw.circle(screen, WHITE, point, 3)

    def _draw_spray_particles(self, screen: pygame.Surface):
        """繪製噴灑粒子"""
        for p in self.spray_particles:
            alpha = int(200 * p['life'])
            size = int(p['size'] * p['life'])
            if size > 0 and alpha > 0:
                color = (*SILICON_BLUE, alpha)
                surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
                pygame.draw.circle(surf, color, (size, size), size)
                screen.blit(surf, (int(p['x']) - size, int(p['y']) - size))
