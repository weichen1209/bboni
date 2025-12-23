"""
階段指示器元件
顯示遊戲進度的視覺化元件
"""

import pygame
import math
from ..config import (
    PRIMARY_COLOR, SECONDARY_COLOR, ACCENT_COLOR,
    WHITE, GRAY, DARK_GRAY, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    GLOW_GREEN, GLOW_BLUE
)
from ..utils.animations import lerp_color, PulseAnimation


class StageIndicator:
    """階段進度指示器"""

    def __init__(self, x: int, y: int, stages: list,
                 current_stage: int = 0,
                 spacing: int = 100,
                 node_radius: int = 16):
        """
        初始化階段指示器

        Args:
            x, y: 中心位置
            stages: 階段名稱列表
            current_stage: 當前階段索引
            spacing: 節點間距
            node_radius: 節點半徑
        """
        self.x = x
        self.y = y
        self.stages = stages
        self._current_stage = current_stage
        self.spacing = spacing
        self.node_radius = node_radius

        # 計算起始位置
        total_width = (len(stages) - 1) * spacing
        self.start_x = x - total_width // 2

        # 動畫
        self.pulse = PulseAnimation(speed=3.0, min_val=0.7, max_val=1.0)
        self.glow_phase = 0.0

        # 字體
        self._font = None

    @property
    def font(self):
        if self._font is None:
            self._font = pygame.font.SysFont("Microsoft JhengHei", 14)
        return self._font

    @property
    def current_stage(self) -> int:
        return self._current_stage

    @current_stage.setter
    def current_stage(self, value: int):
        self._current_stage = max(0, min(len(self.stages) - 1, value))

    def update(self, dt: float):
        """更新動畫"""
        self.pulse.update(dt)
        self.glow_phase += dt * 2

    def draw(self, screen: pygame.Surface):
        """繪製階段指示器"""
        # 繪製連接線
        self._draw_connections(screen)

        # 繪製節點
        for i, stage_name in enumerate(self.stages):
            node_x = self.start_x + i * self.spacing
            self._draw_node(screen, node_x, self.y, i, stage_name)

    def _draw_connections(self, screen: pygame.Surface):
        """繪製節點間的連接線"""
        for i in range(len(self.stages) - 1):
            start_x = self.start_x + i * self.spacing + self.node_radius
            end_x = self.start_x + (i + 1) * self.spacing - self.node_radius

            if i < self._current_stage:
                # 已完成的連接線 - 漸層綠色
                self._draw_gradient_line(screen, start_x, end_x, self.y,
                                        SECONDARY_COLOR, GLOW_GREEN, 4)
            else:
                # 未完成的連接線 - 灰色虛線
                self._draw_dashed_line(screen, start_x, end_x, self.y,
                                      DARK_GRAY, 2, 8)

    def _draw_gradient_line(self, screen: pygame.Surface, x1: int, x2: int, y: int,
                           color1: tuple, color2: tuple, thickness: int):
        """繪製漸層線條"""
        length = x2 - x1
        for x in range(x1, x2):
            t = (x - x1) / max(1, length)
            color = lerp_color(color1, color2, t)
            pygame.draw.line(screen, color, (x, y), (x + 1, y), thickness)

    def _draw_dashed_line(self, screen: pygame.Surface, x1: int, x2: int, y: int,
                         color: tuple, thickness: int, dash_length: int):
        """繪製虛線"""
        x = x1
        draw = True
        while x < x2:
            if draw:
                end_x = min(x + dash_length, x2)
                pygame.draw.line(screen, color, (x, y), (end_x, y), thickness)
            x += dash_length
            draw = not draw

    def _draw_node(self, screen: pygame.Surface, x: int, y: int,
                  index: int, name: str):
        """繪製單個節點"""
        is_completed = index < self._current_stage
        is_current = index == self._current_stage
        is_future = index > self._current_stage

        radius = self.node_radius

        if is_current:
            # 當前節點 - 脈動光暈效果
            self._draw_current_node(screen, x, y, radius)
        elif is_completed:
            # 已完成節點 - 綠色帶勾選
            self._draw_completed_node(screen, x, y, radius)
        else:
            # 未來節點 - 灰色空心
            self._draw_future_node(screen, x, y, radius)

        # 繪製標籤
        self._draw_label(screen, x, y + radius + 20, name, is_current, is_completed)

    def _draw_current_node(self, screen: pygame.Surface, x: int, y: int, radius: int):
        """繪製當前節點"""
        pulse_value = self.pulse.value

        # 外圈光暈
        for i in range(3):
            glow_radius = radius + 8 + i * 4
            alpha = int(60 * pulse_value * (3 - i) / 3)
            glow_surf = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (*ACCENT_COLOR, alpha),
                             (glow_radius, glow_radius), glow_radius)
            screen.blit(glow_surf, (x - glow_radius, y - glow_radius))

        # 主圓
        pygame.draw.circle(screen, ACCENT_COLOR, (x, y), radius)

        # 內圈高光
        inner_radius = int(radius * 0.6)
        highlight_color = tuple(min(255, c + 50) for c in ACCENT_COLOR)
        pygame.draw.circle(screen, highlight_color, (x - 2, y - 2), inner_radius)

        # 邊框
        pygame.draw.circle(screen, WHITE, (x, y), radius, 2)

        # 數字
        num_font = pygame.font.SysFont("Microsoft JhengHei", int(radius * 0.9), bold=True)
        num_text = num_font.render(str(index + 1), True, WHITE)
        num_rect = num_text.get_rect(center=(x, y))
        screen.blit(num_text, num_rect)

    def _draw_completed_node(self, screen: pygame.Surface, x: int, y: int, radius: int):
        """繪製已完成節點"""
        # 外圈光暈
        glow_radius = radius + 5
        glow_surf = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*GLOW_GREEN, 40),
                         (glow_radius, glow_radius), glow_radius)
        screen.blit(glow_surf, (x - glow_radius, y - glow_radius))

        # 主圓
        pygame.draw.circle(screen, SECONDARY_COLOR, (x, y), radius)

        # 邊框
        pygame.draw.circle(screen, WHITE, (x, y), radius, 2)

        # 勾選符號
        check_size = int(radius * 0.5)
        points = [
            (x - check_size, y),
            (x - check_size // 3, y + check_size * 0.6),
            (x + check_size, y - check_size * 0.4)
        ]
        pygame.draw.lines(screen, WHITE, False, points, 3)

    def _draw_future_node(self, screen: pygame.Surface, x: int, y: int, radius: int):
        """繪製未來節點"""
        # 空心圓
        pygame.draw.circle(screen, DARK_GRAY, (x, y), radius)
        pygame.draw.circle(screen, GRAY, (x, y), radius, 2)

        # 數字
        num_font = pygame.font.SysFont("Microsoft JhengHei", int(radius * 0.9))
        num_text = num_font.render(str(index + 1), True, TEXT_MUTED)
        num_rect = num_text.get_rect(center=(x, y))
        # 需要計算 index，暫時用位置推算
        # 這裡簡化處理，不顯示數字

    def _draw_label(self, screen: pygame.Surface, x: int, y: int,
                   text: str, is_current: bool, is_completed: bool):
        """繪製標籤"""
        if is_current:
            color = ACCENT_COLOR
        elif is_completed:
            color = TEXT_PRIMARY
        else:
            color = TEXT_MUTED

        text_surface = self.font.render(text, True, color)
        text_rect = text_surface.get_rect(center=(x, y))
        screen.blit(text_surface, text_rect)


class MiniStageIndicator:
    """迷你階段指示器（用於標題列）"""

    def __init__(self, x: int, y: int, total_stages: int,
                 current_stage: int = 0,
                 dot_size: int = 8,
                 spacing: int = 20):
        """
        初始化迷你指示器

        Args:
            x, y: 中心位置
            total_stages: 總階段數
            current_stage: 當前階段
            dot_size: 點的大小
            spacing: 間距
        """
        self.x = x
        self.y = y
        self.total_stages = total_stages
        self._current_stage = current_stage
        self.dot_size = dot_size
        self.spacing = spacing

        total_width = (total_stages - 1) * spacing
        self.start_x = x - total_width // 2

        self.pulse_phase = 0.0

    @property
    def current_stage(self) -> int:
        return self._current_stage

    @current_stage.setter
    def current_stage(self, value: int):
        self._current_stage = max(0, min(self.total_stages - 1, value))

    def update(self, dt: float):
        """更新動畫"""
        self.pulse_phase += dt * 4

    def draw(self, screen: pygame.Surface):
        """繪製迷你指示器"""
        for i in range(self.total_stages):
            dot_x = self.start_x + i * self.spacing
            is_completed = i < self._current_stage
            is_current = i == self._current_stage

            if is_current:
                # 當前 - 脈動效果
                pulse = 0.7 + 0.3 * math.sin(self.pulse_phase)
                size = int(self.dot_size * (0.9 + pulse * 0.2))
                pygame.draw.circle(screen, ACCENT_COLOR, (dot_x, self.y), size)
                pygame.draw.circle(screen, WHITE, (dot_x, self.y), size, 1)
            elif is_completed:
                # 已完成 - 綠色
                pygame.draw.circle(screen, SECONDARY_COLOR, (dot_x, self.y), self.dot_size)
            else:
                # 未完成 - 灰色空心
                pygame.draw.circle(screen, GRAY, (dot_x, self.y), self.dot_size, 2)
