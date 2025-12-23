"""
增強版進度條元件
帶漸層填充、光澤動畫、里程碑標記
"""

import pygame
import math
from ..config import (
    PRIMARY_COLOR, PRIMARY_LIGHT, SECONDARY_COLOR,
    WHITE, DARK_GRAY, BG_DARK, BG_MEDIUM, GRAY,
    PROGRESSBAR_CORNER_RADIUS, TEXT_PRIMARY, TEXT_SECONDARY,
    ACCENT_COLOR, DANGER_COLOR, GLOW_GREEN
)
from ..utils.animations import lerp, lerp_color, ValueAnimator


class EnhancedProgressBar:
    """增強版進度條"""

    def __init__(self, x: int, y: int, width: int, height: int,
                 bg_color: tuple = BG_DARK,
                 fill_color: tuple = PRIMARY_COLOR,
                 fill_color_end: tuple = None,
                 border_color: tuple = GRAY,
                 show_percentage: bool = True,
                 show_milestones: bool = False,
                 glow_threshold: float = 0.9,
                 animate_value: bool = True):
        """
        初始化進度條

        Args:
            x, y: 位置
            width, height: 尺寸
            bg_color: 背景顏色
            fill_color: 填充起始顏色
            fill_color_end: 填充結束顏色（漸層用）
            border_color: 邊框顏色
            show_percentage: 是否顯示百分比
            show_milestones: 是否顯示里程碑標記
            glow_threshold: 開始發光的閾值 (0-1)
            animate_value: 是否動畫化數值變化
        """
        self.rect = pygame.Rect(x, y, width, height)
        self.bg_color = bg_color
        self.fill_color = fill_color
        self.fill_color_end = fill_color_end or fill_color
        self.border_color = border_color
        self.show_percentage = show_percentage
        self.show_milestones = show_milestones
        self.glow_threshold = glow_threshold

        # 進度值
        self._target_progress = 0.0
        self._animator = ValueAnimator(0.0) if animate_value else None
        self._progress = 0.0

        # 動畫狀態
        self.shine_offset = -0.3
        self.pulse_phase = 0.0
        self.glow_intensity = 0.0

        # 里程碑
        self.milestones = [0.25, 0.5, 0.75]

        # 字體
        self._font = None

    @property
    def font(self):
        if self._font is None:
            self._font = pygame.font.SysFont("Microsoft JhengHei", max(12, self.rect.height - 8))
        return self._font

    @property
    def progress(self) -> float:
        return self._progress

    def set_progress(self, value: float):
        """設定進度 (0.0 ~ 1.0)"""
        self._target_progress = max(0.0, min(1.0, value))
        if self._animator:
            self._animator.set_target(self._target_progress)
        else:
            self._progress = self._target_progress

    def update(self, dt: float):
        """更新動畫狀態"""
        # 更新進度值動畫
        if self._animator:
            self._progress = self._animator.update(dt)
        else:
            self._progress = self._target_progress

        # 光澤動畫
        self.shine_offset += dt * 0.8
        if self.shine_offset > 1.3:
            self.shine_offset = -0.3

        # 脈動動畫（接近完成時）
        if self._progress >= self.glow_threshold:
            self.pulse_phase += dt * 4
            self.glow_intensity = min(1.0, self.glow_intensity + dt * 2)
        else:
            self.glow_intensity = max(0.0, self.glow_intensity - dt * 3)

    def draw(self, screen: pygame.Surface):
        """繪製進度條"""
        # 1. 繪製光暈（如果接近完成）
        if self.glow_intensity > 0.01:
            self._draw_glow(screen)

        # 2. 繪製背景
        self._draw_background(screen)

        # 3. 繪製填充
        if self._progress > 0:
            self._draw_fill(screen)

        # 4. 繪製光澤
        if self._progress > 0.1:
            self._draw_shine(screen)

        # 5. 繪製里程碑
        if self.show_milestones:
            self._draw_milestones(screen)

        # 6. 繪製邊框
        self._draw_border(screen)

        # 7. 繪製百分比
        if self.show_percentage:
            self._draw_percentage(screen)

    def _draw_glow(self, screen: pygame.Surface):
        """繪製發光效果"""
        glow_size = 8
        pulse = 0.7 + 0.3 * math.sin(self.pulse_phase)
        glow_rect = self.rect.inflate(glow_size * 2, glow_size * 2)

        glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)

        for i in range(3):
            alpha = int(40 * self.glow_intensity * pulse * (3 - i) / 3)
            inflate = i * 3
            inner_rect = pygame.Rect(glow_size - inflate, glow_size - inflate,
                                    self.rect.width + inflate * 2,
                                    self.rect.height + inflate * 2)
            glow_color = (*GLOW_GREEN, alpha)
            pygame.draw.rect(glow_surf, glow_color, inner_rect,
                           border_radius=PROGRESSBAR_CORNER_RADIUS + inflate)

        screen.blit(glow_surf, glow_rect.topleft)

    def _draw_background(self, screen: pygame.Surface):
        """繪製背景"""
        # 漸層背景
        bg_surf = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)

        for y in range(self.rect.height):
            ratio = y / self.rect.height
            brightness = 0.8 + ratio * 0.4
            row_color = tuple(min(255, int(c * brightness)) for c in self.bg_color)
            pygame.draw.line(bg_surf, (*row_color, 255), (0, y), (self.rect.width, y))

        # 應用圓角
        mask_surf = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        pygame.draw.rect(mask_surf, (255, 255, 255, 255),
                        (0, 0, self.rect.width, self.rect.height),
                        border_radius=PROGRESSBAR_CORNER_RADIUS)
        bg_surf.blit(mask_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)

        screen.blit(bg_surf, self.rect.topleft)

    def _draw_fill(self, screen: pygame.Surface):
        """繪製填充"""
        fill_width = int(self.rect.width * self._progress)
        if fill_width <= 0:
            return

        fill_surf = pygame.Surface((fill_width, self.rect.height), pygame.SRCALPHA)

        # 漸層填充（水平 + 垂直）
        for x in range(fill_width):
            x_ratio = x / max(1, fill_width)
            col_color = lerp_color(self.fill_color, self.fill_color_end, x_ratio)

            for y in range(self.rect.height):
                y_ratio = y / self.rect.height
                # 上方較亮
                brightness = 1.2 - y_ratio * 0.4
                pixel_color = tuple(min(255, int(c * brightness)) for c in col_color)
                fill_surf.set_at((x, y), (*pixel_color, 255))

        # 應用圓角
        mask_surf = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        pygame.draw.rect(mask_surf, (255, 255, 255, 255),
                        (0, 0, self.rect.width, self.rect.height),
                        border_radius=PROGRESSBAR_CORNER_RADIUS)

        # 裁切到填充區域
        fill_mask = pygame.Surface((fill_width, self.rect.height), pygame.SRCALPHA)
        fill_mask.blit(mask_surf, (0, 0))
        fill_surf.blit(fill_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)

        screen.blit(fill_surf, self.rect.topleft)

    def _draw_shine(self, screen: pygame.Surface):
        """繪製光澤效果"""
        fill_width = int(self.rect.width * self._progress)
        if fill_width <= 10:
            return

        shine_surf = pygame.Surface((fill_width, self.rect.height), pygame.SRCALPHA)

        # 對角線光澤
        shine_width = fill_width * 0.25
        x_pos = int(self.shine_offset * (fill_width + shine_width) - shine_width)

        for i in range(int(shine_width)):
            alpha = int(80 * (1 - abs(i - shine_width/2) / (shine_width/2)))
            x = x_pos + i
            if 0 <= x < fill_width:
                pygame.draw.line(shine_surf, (255, 255, 255, alpha),
                               (x, 0), (x, self.rect.height))

        # 頂部高光線
        highlight_alpha = 60
        pygame.draw.line(shine_surf, (255, 255, 255, highlight_alpha),
                        (3, 2), (fill_width - 3, 2), 1)

        # 應用圓角遮罩
        mask_surf = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        pygame.draw.rect(mask_surf, (255, 255, 255, 255),
                        (0, 0, self.rect.width, self.rect.height),
                        border_radius=PROGRESSBAR_CORNER_RADIUS)
        fill_mask = pygame.Surface((fill_width, self.rect.height), pygame.SRCALPHA)
        fill_mask.blit(mask_surf, (0, 0))
        shine_surf.blit(fill_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)

        screen.blit(shine_surf, self.rect.topleft)

    def _draw_milestones(self, screen: pygame.Surface):
        """繪製里程碑標記"""
        for milestone in self.milestones:
            x = self.rect.x + int(self.rect.width * milestone)

            # 標記線
            if self._progress >= milestone:
                color = (*WHITE, 180)
            else:
                color = (*GRAY, 100)

            pygame.draw.line(screen, color,
                           (x, self.rect.y + 2),
                           (x, self.rect.y + self.rect.height - 2), 1)

    def _draw_border(self, screen: pygame.Surface):
        """繪製邊框"""
        # 內陰影效果
        pygame.draw.rect(screen, self.border_color, self.rect,
                        width=1, border_radius=PROGRESSBAR_CORNER_RADIUS)

        # 如果發光，加亮邊框
        if self.glow_intensity > 0.01:
            pulse = 0.7 + 0.3 * math.sin(self.pulse_phase)
            border_glow = lerp_color(self.border_color, GLOW_GREEN, self.glow_intensity * pulse * 0.5)
            pygame.draw.rect(screen, border_glow, self.rect,
                           width=2, border_radius=PROGRESSBAR_CORNER_RADIUS)

    def _draw_percentage(self, screen: pygame.Surface):
        """繪製百分比文字"""
        percent = int(self._progress * 100)
        text = f"{percent}%"

        text_surface = self.font.render(text, True, TEXT_PRIMARY)
        text_rect = text_surface.get_rect()

        # 如果進度條夠寬，文字在內部
        if self.rect.width > 100 and self.rect.height > 20:
            text_rect.center = self.rect.center
        else:
            # 否則在右側
            text_rect.midleft = (self.rect.right + 10, self.rect.centery)

        screen.blit(text_surface, text_rect)


class CircularProgressBar:
    """圓形進度條"""

    def __init__(self, x: int, y: int, radius: int,
                 thickness: int = 10,
                 bg_color: tuple = BG_DARK,
                 fill_color: tuple = PRIMARY_COLOR,
                 fill_color_end: tuple = None):
        """
        初始化圓形進度條

        Args:
            x, y: 圓心位置
            radius: 半徑
            thickness: 線條粗細
            bg_color: 背景顏色
            fill_color: 填充起始顏色
            fill_color_end: 填充結束顏色
        """
        self.center = (x, y)
        self.radius = radius
        self.thickness = thickness
        self.bg_color = bg_color
        self.fill_color = fill_color
        self.fill_color_end = fill_color_end or fill_color

        self._progress = 0.0
        self._animator = ValueAnimator(0.0)

    def set_progress(self, value: float):
        """設定進度 (0.0 ~ 1.0)"""
        self._animator.set_target(max(0.0, min(1.0, value)))

    def update(self, dt: float):
        """更新動畫"""
        self._progress = self._animator.update(dt)

    def draw(self, screen: pygame.Surface):
        """繪製圓形進度條"""
        cx, cy = self.center

        # 繪製背景圓
        pygame.draw.circle(screen, self.bg_color, self.center, self.radius, self.thickness)

        # 繪製進度弧
        if self._progress > 0:
            # 使用多段線模擬弧線
            start_angle = -math.pi / 2  # 從頂部開始
            end_angle = start_angle + self._progress * 2 * math.pi

            points = []
            segments = max(10, int(60 * self._progress))
            for i in range(segments + 1):
                angle = start_angle + (end_angle - start_angle) * i / segments
                x = cx + self.radius * math.cos(angle)
                y = cy + self.radius * math.sin(angle)
                points.append((x, y))

            if len(points) >= 2:
                # 漸層顏色
                for i in range(len(points) - 1):
                    t = i / max(1, len(points) - 1)
                    color = lerp_color(self.fill_color, self.fill_color_end, t)
                    pygame.draw.line(screen, color, points[i], points[i + 1], self.thickness)

    @property
    def progress(self) -> float:
        return self._progress
