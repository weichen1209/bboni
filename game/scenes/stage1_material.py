"""
第一關：準備材料
玩家搖晃感測器，模擬沙子熔煉成多晶矽、單晶矽晶柱、晶圓的過程
"""

import pygame
import math
from .base import Scene, Button, ProgressBar
from ..config import *


class MaterialStage(Scene):
    """材料準備關卡"""

    # 4 階段材料定義
    STAGES = [
        {"name": "沙子", "color": SAND_YELLOW},
        {"name": "多晶矽", "color": POLYSILICON_GRAY},
        {"name": "單晶矽晶柱", "color": SILICON_BLUE},
        {"name": "晶圓", "color": SILICON_BLUE},
    ]

    # 遊戲參數
    ENERGY_SPEED = 0.4          # 能量累積速度
    MIN_SHAKE_THRESHOLD = 0.1   # 有效搖晃最低門檻
    SAMPLE_WINDOW = 50          # 均勻度計算樣本數
    VARIANCE_PENALTY = 200      # 變異度扣分係數

    def __init__(self, game):
        super().__init__(game)

        # 遊戲狀態
        self.current_stage = 0
        self.energy = 0.0
        self.shake_samples = []     # 搖晃強度樣本（計算均勻度）
        self.stage_scores = []      # 各階段分數
        self.is_complete = False

        # 動畫
        self.particle_angle = 0     # 粒子旋轉角度
        self.glow_intensity = 0     # 發光強度

        # UI 元件
        center_x = SCREEN_WIDTH // 2
        self.progress_bar = ProgressBar(
            center_x - 250, 520, 500, 35,
            bg_color=DARK_GRAY,
            fill_color=ACCENT_COLOR,
            border_color=GRAY
        )

        self.next_button = Button(
            center_x - 100, 620, 200, 50,
            "繼續", PRIMARY_COLOR
        )

        # 字體
        self.title_font = None
        self.text_font = None
        self.small_font = None

    def on_enter(self):
        """進入場景"""
        self.title_font = pygame.font.SysFont("Microsoft JhengHei", 36)
        self.text_font = pygame.font.SysFont("Microsoft JhengHei", 24)
        self.small_font = pygame.font.SysFont("Microsoft JhengHei", 18)

        # 預繪製所有階段的漸層背景（效能優化）
        self._bg_surfaces = []
        for stage in self.STAGES:
            color = stage["color"]
            surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            for y in range(SCREEN_HEIGHT):
                ratio = y / SCREEN_HEIGHT
                r = int(20 + (color[0] - 20) * ratio * 0.3)
                g = int(25 + (color[1] - 25) * ratio * 0.3)
                b = int(40 + (color[2] - 40) * ratio * 0.3)
                pygame.draw.line(surf, (r, g, b), (0, y), (SCREEN_WIDTH, y))
            self._bg_surfaces.append(surf)

        # 重置狀態
        self.current_stage = 0
        self.energy = 0.0
        self.shake_samples = []
        self.stage_scores = []
        self.is_complete = False

    def handle_event(self, event: pygame.event.Event):
        """處理事件"""
        if self.is_complete:
            if self.next_button.handle_event(event):
                self._finish_stage()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE or event.key == pygame.K_RETURN:
                    self._finish_stage()

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.switch_to("menu")

    def _get_shake_intensity(self) -> float:
        """取得搖晃強度"""
        if self.game.sensor and self.game.sensor.is_connected:
            return self.game.sensor.get_shake_intensity()
        return 0.0

    def _calculate_purity_score(self) -> int:
        """計算純度分數（0-100）- 基於搖晃均勻度"""
        if len(self.shake_samples) < 10:
            return 50  # 樣本太少，給基本分

        # 計算標準差
        mean = sum(self.shake_samples) / len(self.shake_samples)
        variance = sum((x - mean) ** 2 for x in self.shake_samples) / len(self.shake_samples)
        std_dev = variance ** 0.5

        # 均勻度分數（標準差越小分數越高）
        score = max(0, 100 - std_dev * self.VARIANCE_PENALTY)
        return int(score)

    def _advance_stage(self):
        """進入下一階段"""
        # 記錄當前階段分數
        score = self._calculate_purity_score()
        self.stage_scores.append(score)

        # 清空樣本，重置能量
        self.shake_samples = []
        self.energy = 0.0
        self.current_stage += 1

        # 檢查是否完成所有階段
        if self.current_stage >= len(self.STAGES):
            self.current_stage = len(self.STAGES) - 1
            self.is_complete = True
            self._save_score()

    def _save_score(self):
        """儲存純度分數"""
        if self.stage_scores:
            avg_score = sum(self.stage_scores) / len(self.stage_scores)
            self.game.scores["purity"] = int(avg_score)

    def _finish_stage(self):
        """完成關卡，進入下一關"""
        self.switch_to("stage2")

    def update(self, dt: float):
        """更新遊戲邏輯"""
        if self.is_complete:
            return

        # 取得搖晃強度
        intensity = self._get_shake_intensity()

        # 更新動畫
        self.particle_angle += dt * 100 * (intensity + 0.1)
        self.glow_intensity = min(1.0, self.glow_intensity + intensity * dt * 5)
        self.glow_intensity = max(0.0, self.glow_intensity - dt * 2)

        # 累積能量
        if intensity > self.MIN_SHAKE_THRESHOLD:
            self.energy += intensity * dt * self.ENERGY_SPEED
            self.shake_samples.append(intensity)

            # 限制樣本數量
            if len(self.shake_samples) > self.SAMPLE_WINDOW:
                self.shake_samples.pop(0)

        # 更新進度條
        self.progress_bar.set_progress(self.energy)

        # 檢查階段轉換
        if self.energy >= 1.0:
            self._advance_stage()

    def draw(self, screen: pygame.Surface):
        """繪製場景"""
        # 漸層背景
        self._draw_background(screen)

        # 標題
        stage_name = self.STAGES[self.current_stage]["name"]
        title_text = f"準備材料 - {stage_name}"
        if self.is_complete:
            title_text = "材料準備完成！"

        title_surface = self.title_font.render(title_text, True, WHITE)
        title_rect = title_surface.get_rect(center=(SCREEN_WIDTH // 2, 50))
        screen.blit(title_surface, title_rect)

        # 階段指示器
        self._draw_stage_indicators(screen)

        # 材料視覺化
        self._draw_material(screen)

        # 提示文字
        if not self.is_complete:
            hint = "搖晃裝置來轉化材料！"
            hint_surface = self.text_font.render(hint, True, LIGHT_GRAY)
            hint_rect = hint_surface.get_rect(center=(SCREEN_WIDTH // 2, 470))
            screen.blit(hint_surface, hint_rect)

            # 進度條
            self.progress_bar.draw(screen)

            # 能量百分比
            percent_text = f"{int(self.energy * 100)}%"
            percent_surface = self.text_font.render(percent_text, True, WHITE)
            percent_rect = percent_surface.get_rect(center=(SCREEN_WIDTH // 2, 580))
            screen.blit(percent_surface, percent_rect)

        else:
            # 顯示分數
            avg_score = sum(self.stage_scores) / len(self.stage_scores) if self.stage_scores else 0
            score_text = f"純度評分: {int(avg_score)} 分"
            score_surface = self.title_font.render(score_text, True, SECONDARY_COLOR)
            score_rect = score_surface.get_rect(center=(SCREEN_WIDTH // 2, 520))
            screen.blit(score_surface, score_rect)

            # 繼續按鈕
            self.next_button.draw(screen)

    def _draw_background(self, screen: pygame.Surface):
        """繪製漸層背景（使用預繪製的快取）"""
        screen.blit(self._bg_surfaces[self.current_stage], (0, 0))

    def _draw_stage_indicators(self, screen: pygame.Surface):
        """繪製階段進度指示器"""
        center_x = SCREEN_WIDTH // 2
        y = 100
        spacing = 80
        start_x = center_x - (len(self.STAGES) - 1) * spacing // 2

        for i, stage in enumerate(self.STAGES):
            x = start_x + i * spacing

            # 圓點
            if i < self.current_stage:
                color = SECONDARY_COLOR  # 已完成
            elif i == self.current_stage:
                color = ACCENT_COLOR     # 當前
            else:
                color = GRAY             # 未完成

            pygame.draw.circle(screen, color, (x, y), 12)
            pygame.draw.circle(screen, WHITE, (x, y), 12, 2)

            # 階段名稱
            name_surface = self.small_font.render(stage["name"], True, LIGHT_GRAY)
            name_rect = name_surface.get_rect(center=(x, y + 30))
            screen.blit(name_surface, name_rect)

            # 連接線
            if i < len(self.STAGES) - 1:
                line_color = SECONDARY_COLOR if i < self.current_stage else GRAY
                pygame.draw.line(screen, line_color, (x + 15, y), (x + spacing - 15, y), 2)

    def _draw_material(self, screen: pygame.Surface):
        """繪製材料視覺化"""
        center_x = SCREEN_WIDTH // 2
        center_y = 300
        current_color = self.STAGES[self.current_stage]["color"]

        if self.current_stage == 0:
            # 沙子：散落的顆粒
            self._draw_sand(screen, center_x, center_y, current_color)
        elif self.current_stage == 1:
            # 多晶矽：不規則多邊形
            self._draw_polysilicon(screen, center_x, center_y, current_color)
        elif self.current_stage == 2:
            # 單晶矽晶柱：圓柱體
            self._draw_crystal(screen, center_x, center_y, current_color)
        else:
            # 晶圓：圓形薄片
            self._draw_wafer(screen, center_x, center_y, current_color)

    def _draw_sand(self, screen, cx, cy, color):
        """繪製沙子"""
        import random
        random.seed(42)  # 固定種子確保一致性

        for _ in range(80):
            offset_x = random.randint(-100, 100)
            offset_y = random.randint(-60, 60)
            size = random.randint(3, 8)

            # 根據動畫角度微調位置
            angle_offset = math.sin(self.particle_angle * 0.02 + offset_x * 0.1) * 3
            x = cx + offset_x + angle_offset
            y = cy + offset_y

            pygame.draw.circle(screen, color, (int(x), int(y)), size)

        # 發光效果
        if self.glow_intensity > 0:
            glow_surf = pygame.Surface((250, 150), pygame.SRCALPHA)
            glow_color = (*ACCENT_COLOR, int(50 * self.glow_intensity))
            pygame.draw.ellipse(glow_surf, glow_color, (0, 0, 250, 150))
            screen.blit(glow_surf, (cx - 125, cy - 75))

    def _draw_polysilicon(self, screen, cx, cy, color):
        """繪製多晶矽"""
        # 不規則多邊形
        points = []
        num_points = 8
        for i in range(num_points):
            angle = (i / num_points) * 2 * math.pi + self.particle_angle * 0.01
            radius = 60 + math.sin(angle * 3) * 20
            x = cx + math.cos(angle) * radius
            y = cy + math.sin(angle) * radius
            points.append((x, y))

        pygame.draw.polygon(screen, color, points)
        pygame.draw.polygon(screen, WHITE, points, 2)

        # 內部紋理（表示多晶結構）
        for i in range(5):
            angle = (i / 5) * 2 * math.pi
            x1 = cx + math.cos(angle) * 20
            y1 = cy + math.sin(angle) * 20
            x2 = cx + math.cos(angle) * 50
            y2 = cy + math.sin(angle) * 50
            pygame.draw.line(screen, DARK_GRAY, (x1, y1), (x2, y2), 1)

        # 發光效果
        if self.glow_intensity > 0:
            glow_surf = pygame.Surface((200, 200), pygame.SRCALPHA)
            glow_color = (*ACCENT_COLOR, int(60 * self.glow_intensity))
            pygame.draw.circle(glow_surf, glow_color, (100, 100), 80)
            screen.blit(glow_surf, (cx - 100, cy - 100))

    def _draw_crystal(self, screen, cx, cy, color):
        """繪製單晶矽晶柱"""
        # 圓柱體側面（橢圓 + 矩形）
        width = 80
        height = 140

        # 底部橢圓
        pygame.draw.ellipse(screen, DARK_GRAY, (cx - width // 2, cy + height // 2 - 15, width, 30))

        # 側面
        pygame.draw.rect(screen, color, (cx - width // 2, cy - height // 2, width, height))

        # 頂部橢圓
        pygame.draw.ellipse(screen, color, (cx - width // 2, cy - height // 2 - 15, width, 30))

        # 光澤線
        for i in range(3):
            y_pos = cy - height // 2 + 30 + i * 40
            pygame.draw.line(screen, WHITE, (cx - 25, y_pos), (cx - 25, y_pos + 20), 2)

        # 邊框
        pygame.draw.ellipse(screen, WHITE, (cx - width // 2, cy - height // 2 - 15, width, 30), 2)
        pygame.draw.line(screen, WHITE, (cx - width // 2, cy - height // 2), (cx - width // 2, cy + height // 2), 2)
        pygame.draw.line(screen, WHITE, (cx + width // 2, cy - height // 2), (cx + width // 2, cy + height // 2), 2)

        # 發光效果
        if self.glow_intensity > 0:
            glow_surf = pygame.Surface((200, 250), pygame.SRCALPHA)
            glow_color = (*ACCENT_COLOR, int(50 * self.glow_intensity))
            pygame.draw.ellipse(glow_surf, glow_color, (0, 0, 200, 250))
            screen.blit(glow_surf, (cx - 100, cy - 125))

    def _draw_wafer(self, screen, cx, cy, color):
        """繪製晶圓"""
        radius = 90

        # 主圓
        pygame.draw.circle(screen, color, (cx, cy), radius)

        # 彩虹反射效果（晶圓特有的）
        for i, rainbow_color in enumerate(WAFER_RAINBOW):
            angle = (i / len(WAFER_RAINBOW)) * 2 * math.pi + self.particle_angle * 0.02
            arc_rect = pygame.Rect(cx - radius + 10, cy - radius + 10, (radius - 10) * 2, (radius - 10) * 2)
            pygame.draw.arc(screen, rainbow_color, arc_rect, angle, angle + 0.5, 3)

        # 晶格圖案
        for i in range(-8, 9):
            for j in range(-8, 9):
                x = cx + i * 10
                y = cy + j * 10
                dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
                if dist < radius - 5:
                    pygame.draw.circle(screen, DARK_GRAY, (x, y), 1)

        # 邊框
        pygame.draw.circle(screen, WHITE, (cx, cy), radius, 3)

        # 缺口（wafer flat）
        flat_points = [
            (cx - 20, cy + radius - 5),
            (cx + 20, cy + radius - 5),
            (cx + 20, cy + radius + 5),
            (cx - 20, cy + radius + 5),
        ]
        pygame.draw.polygon(screen, (30, 40, 60), flat_points)

        # 發光效果
        if self.glow_intensity > 0:
            glow_surf = pygame.Surface((250, 250), pygame.SRCALPHA)
            glow_color = (*SECONDARY_COLOR, int(40 * self.glow_intensity))
            pygame.draw.circle(glow_surf, glow_color, (125, 125), 110)
            screen.blit(glow_surf, (cx - 125, cy - 125))
