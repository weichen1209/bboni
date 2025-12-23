"""
場景基礎類別
"""

import pygame
import math
from abc import ABC, abstractmethod
from ..utils.drawing import create_gradient_surface
from ..config import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    BG_DARK, BG_MEDIUM, WHITE, TEXT_MUTED
)


class Scene(ABC):
    """場景基礎類別"""

    def __init__(self, game):
        """
        初始化場景
        game: Game 實例
        """
        self.game = game
        self.next_scene = None  # 下一個場景名稱
        self.finished = False   # 是否完成此場景
        self._gradient_surface = None  # 預繪製漸層背景緩存

        # 場景過渡動畫
        self._fade_alpha = 0
        self._fade_in = False
        self._fade_out = False

        # 背景粒子
        self._bg_particles = []

    @abstractmethod
    def handle_event(self, event: pygame.event.Event):
        """處理事件"""
        pass

    @abstractmethod
    def update(self, dt: float):
        """
        更新場景
        dt: 距離上一幀的時間 (秒)
        """
        pass

    @abstractmethod
    def draw(self, screen: pygame.Surface):
        """繪製場景"""
        pass

    def on_enter(self):
        """進入場景時調用"""
        self._fade_in = True
        self._fade_alpha = 255

    def on_exit(self):
        """離開場景時調用"""
        pass

    def switch_to(self, scene_name: str):
        """切換到指定場景"""
        self.next_scene = scene_name
        self.finished = True

    def create_gradient_background(self, base_color: tuple, factor: float = 1.0) -> pygame.Surface:
        """創建預繪製的漸層背景"""
        return create_gradient_surface(base_color, factor=factor)

    def create_enhanced_background(self, base_color: tuple,
                                   add_vignette: bool = True,
                                   add_grid: bool = False) -> pygame.Surface:
        """
        創建增強版背景

        Args:
            base_color: 基礎顏色
            add_vignette: 是否加入暗角效果
            add_grid: 是否加入網格圖案
        """
        surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))

        # 基礎漸層
        for y in range(SCREEN_HEIGHT):
            ratio = y / SCREEN_HEIGHT
            r = int(BG_DARK[0] + (base_color[0] - BG_DARK[0]) * ratio * 0.3)
            g = int(BG_DARK[1] + (base_color[1] - BG_DARK[1]) * ratio * 0.3)
            b = int(BG_DARK[2] + (base_color[2] - BG_DARK[2]) * ratio * 0.4)
            pygame.draw.line(surf, (r, g, b), (0, y), (SCREEN_WIDTH, y))

        # 網格圖案
        if add_grid:
            grid_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            grid_color = (255, 255, 255, 8)
            grid_spacing = 50
            for x in range(0, SCREEN_WIDTH, grid_spacing):
                pygame.draw.line(grid_surf, grid_color, (x, 0), (x, SCREEN_HEIGHT))
            for y in range(0, SCREEN_HEIGHT, grid_spacing):
                pygame.draw.line(grid_surf, grid_color, (0, y), (SCREEN_WIDTH, y))
            surf.blit(grid_surf, (0, 0))

        # 暗角效果
        if add_vignette:
            vignette = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            center_x, center_y = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
            max_dist = math.sqrt(center_x**2 + center_y**2)

            for y in range(0, SCREEN_HEIGHT, 4):
                for x in range(0, SCREEN_WIDTH, 4):
                    dist = math.sqrt((x - center_x)**2 + (y - center_y)**2)
                    alpha = int(80 * (dist / max_dist) ** 1.5)
                    pygame.draw.rect(vignette, (0, 0, 0, alpha), (x, y, 4, 4))
            surf.blit(vignette, (0, 0))

        return surf

    def render_text(self, font: pygame.font.Font, text: str, color: tuple) -> pygame.Surface:
        """渲染文字（帶快取）"""
        cache_key = (id(font), text, color)
        if not hasattr(self, '_text_cache'):
            self._text_cache = {}
        if cache_key not in self._text_cache:
            self._text_cache[cache_key] = font.render(text, True, color)
        return self._text_cache[cache_key]

    def render_text_with_shadow(self, font: pygame.font.Font, text: str,
                               color: tuple, shadow_color: tuple = (0, 0, 0),
                               offset: tuple = (2, 2)) -> pygame.Surface:
        """渲染帶陰影的文字"""
        text_surface = font.render(text, True, color)
        shadow_surface = font.render(text, True, shadow_color)

        # 創建合併的 surface
        result = pygame.Surface(
            (text_surface.get_width() + abs(offset[0]),
             text_surface.get_height() + abs(offset[1])),
            pygame.SRCALPHA
        )

        # 繪製陰影
        result.blit(shadow_surface, (max(0, offset[0]), max(0, offset[1])))
        # 繪製文字
        result.blit(text_surface, (max(0, -offset[0]), max(0, -offset[1])))

        return result

    def draw_title(self, screen: pygame.Surface, text: str, y: int = 50,
                  font: pygame.font.Font = None, color: tuple = WHITE):
        """繪製標題"""
        if font is None:
            font = pygame.font.SysFont("Microsoft JhengHei", 42)

        # 主文字
        title_surf = font.render(text, True, color)
        title_rect = title_surf.get_rect(center=(SCREEN_WIDTH // 2, y))
        screen.blit(title_surf, title_rect)

    def update_fade(self, dt: float):
        """更新淡入淡出效果"""
        if self._fade_in:
            self._fade_alpha = max(0, self._fade_alpha - dt * 600)
            if self._fade_alpha <= 0:
                self._fade_in = False
        elif self._fade_out:
            self._fade_alpha = min(255, self._fade_alpha + dt * 600)

    def draw_fade_overlay(self, screen: pygame.Surface):
        """繪製淡入淡出遮罩"""
        if self._fade_alpha > 0:
            fade_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            fade_surf.fill((0, 0, 0, int(self._fade_alpha)))
            screen.blit(fade_surf, (0, 0))


class Button:
    """增強版按鈕類別"""

    def __init__(self, x: int, y: int, width: int, height: int,
                 text: str, color=(52, 152, 219), hover_color=(85, 175, 235),
                 text_color=(255, 255, 255), font_size: int = 28):
        self.base_rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.text_color = text_color
        self.font_size = font_size
        self.is_hovered = False
        self.is_pressed = False
        self._font = None

        # 動畫狀態
        self.hover_progress = 0.0
        self.press_progress = 0.0
        self.glow_phase = 0.0

    @property
    def font(self):
        if self._font is None:
            self._font = pygame.font.SysFont("Microsoft JhengHei", self.font_size)
        return self._font

    @property
    def rect(self):
        """取得當前矩形（向後相容）"""
        return self.base_rect

    def handle_event(self, event: pygame.event.Event) -> bool:
        """處理事件，返回是否被點擊"""
        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.base_rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1 and self.base_rect.collidepoint(event.pos):
                self.is_pressed = True
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                was_pressed = self.is_pressed
                self.is_pressed = False
                if was_pressed and self.base_rect.collidepoint(event.pos):
                    return True
        return False

    def update(self, dt: float):
        """更新動畫狀態"""
        # Hover 動畫
        target = 1.0 if self.is_hovered else 0.0
        self.hover_progress += (target - self.hover_progress) * min(1.0, dt * 8)

        # Press 動畫
        target_press = 1.0 if self.is_pressed else 0.0
        self.press_progress += (target_press - self.press_progress) * min(1.0, dt * 12)

        # 光暈動畫
        self.glow_phase += dt * 3

    def draw(self, screen: pygame.Surface):
        """繪製按鈕"""
        rect = self.base_rect

        # 縮放效果
        scale = 1.0 + self.hover_progress * 0.02 - self.press_progress * 0.03
        scaled_width = int(rect.width * scale)
        scaled_height = int(rect.height * scale)
        draw_rect = pygame.Rect(
            rect.centerx - scaled_width // 2,
            rect.centery - scaled_height // 2,
            scaled_width,
            scaled_height
        )

        # 陰影
        shadow_offset = 3
        shadow_rect = draw_rect.move(shadow_offset, shadow_offset)
        shadow_surf = pygame.Surface((shadow_rect.width, shadow_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(shadow_surf, (0, 0, 0, 40), (0, 0, shadow_rect.width, shadow_rect.height),
                        border_radius=12)
        screen.blit(shadow_surf, shadow_rect.topleft)

        # 光暈（hover時）
        if self.hover_progress > 0.01:
            glow_intensity = self.hover_progress * (0.7 + 0.3 * math.sin(self.glow_phase))
            glow_size = 6
            glow_rect = draw_rect.inflate(glow_size * 2, glow_size * 2)
            glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
            glow_alpha = int(50 * glow_intensity)
            pygame.draw.rect(glow_surf, (*self.hover_color, glow_alpha),
                           (0, 0, glow_rect.width, glow_rect.height),
                           border_radius=15)
            screen.blit(glow_surf, glow_rect.topleft)

        # 計算當前顏色
        r = int(self.color[0] + (self.hover_color[0] - self.color[0]) * self.hover_progress)
        g = int(self.color[1] + (self.hover_color[1] - self.color[1]) * self.hover_progress)
        b = int(self.color[2] + (self.hover_color[2] - self.color[2]) * self.hover_progress)
        current_color = (r, g, b)

        # 繪製漸層主體
        body_surf = pygame.Surface((draw_rect.width, draw_rect.height), pygame.SRCALPHA)
        for y in range(draw_rect.height):
            ratio = y / draw_rect.height
            brightness = 1.15 - ratio * 0.3
            row_color = tuple(min(255, int(c * brightness)) for c in current_color)
            pygame.draw.line(body_surf, (*row_color, 255), (0, y), (draw_rect.width, y))

        # 應用圓角
        mask = pygame.Surface((draw_rect.width, draw_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, draw_rect.width, draw_rect.height),
                        border_radius=12)
        body_surf.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        screen.blit(body_surf, draw_rect.topleft)

        # 邊框
        border_color = tuple(min(255, c + 30) for c in current_color)
        pygame.draw.rect(screen, border_color, draw_rect, width=2, border_radius=12)

        # 頂部高光
        highlight_rect = pygame.Rect(draw_rect.x + 10, draw_rect.y + 3,
                                    draw_rect.width - 20, 2)
        pygame.draw.rect(screen, (255, 255, 255, 40), highlight_rect, border_radius=1)

        # 繪製文字
        text_surface = self.font.render(self.text, True, self.text_color)
        text_rect = text_surface.get_rect(center=draw_rect.center)
        if self.is_pressed:
            text_rect.y += 1
        screen.blit(text_surface, text_rect)


class ProgressBar:
    """增強版進度條類別"""

    def __init__(self, x: int, y: int, width: int, height: int,
                 bg_color=(40, 50, 70), fill_color=(52, 152, 219),
                 border_color=(80, 90, 110), fill_color_end=None):
        self.rect = pygame.Rect(x, y, width, height)
        self.bg_color = bg_color
        self.fill_color = fill_color
        self.fill_color_end = fill_color_end or tuple(min(255, c + 40) for c in fill_color)
        self.border_color = border_color
        self.progress = 0.0  # 0.0 ~ 1.0
        self._target_progress = 0.0

        # 動畫狀態
        self.shine_offset = -0.3
        self.glow_phase = 0.0

    def set_progress(self, value: float):
        """設定進度 (0.0 ~ 1.0)"""
        self._target_progress = max(0.0, min(1.0, value))

    def reset(self):
        """立即重置進度到 0（無動畫）"""
        self.progress = 0.0
        self._target_progress = 0.0
        self.shine_offset = -0.3
        self.glow_phase = 0.0

    def update(self, dt: float):
        """更新動畫"""
        # 平滑進度變化
        self.progress += (self._target_progress - self.progress) * min(1.0, dt * 8)

        # 光澤動畫
        self.shine_offset += dt * 0.6
        if self.shine_offset > 1.5:
            self.shine_offset = -0.3

        # 光暈動畫
        self.glow_phase += dt * 3

    def draw(self, screen: pygame.Surface):
        """繪製進度條"""
        # 背景漸層
        bg_surf = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        for y in range(self.rect.height):
            ratio = y / self.rect.height
            brightness = 0.8 + ratio * 0.4
            row_color = tuple(min(255, int(c * brightness)) for c in self.bg_color)
            pygame.draw.line(bg_surf, (*row_color, 255), (0, y), (self.rect.width, y))

        # 應用圓角
        mask = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, self.rect.width, self.rect.height),
                        border_radius=8)
        bg_surf.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        screen.blit(bg_surf, self.rect.topleft)

        # 填充漸層
        if self.progress > 0:
            fill_width = max(1, int(self.rect.width * self.progress))
            fill_surf = pygame.Surface((fill_width, self.rect.height), pygame.SRCALPHA)

            for x in range(fill_width):
                x_ratio = x / max(1, fill_width)
                # 水平漸層
                r = int(self.fill_color[0] + (self.fill_color_end[0] - self.fill_color[0]) * x_ratio)
                g = int(self.fill_color[1] + (self.fill_color_end[1] - self.fill_color[1]) * x_ratio)
                b = int(self.fill_color[2] + (self.fill_color_end[2] - self.fill_color[2]) * x_ratio)

                for y in range(self.rect.height):
                    y_ratio = y / self.rect.height
                    # 垂直光澤
                    brightness = 1.2 - y_ratio * 0.4
                    pixel_color = (
                        min(255, int(r * brightness)),
                        min(255, int(g * brightness)),
                        min(255, int(b * brightness)),
                        255
                    )
                    fill_surf.set_at((x, y), pixel_color)

            # 應用圓角遮罩
            fill_mask = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
            pygame.draw.rect(fill_mask, (255, 255, 255, 255),
                           (0, 0, self.rect.width, self.rect.height), border_radius=8)
            clip_mask = pygame.Surface((fill_width, self.rect.height), pygame.SRCALPHA)
            clip_mask.blit(fill_mask, (0, 0))
            fill_surf.blit(clip_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)

            screen.blit(fill_surf, self.rect.topleft)

            # 光澤效果
            if fill_width > 10:
                self._draw_shine(screen, fill_width)

            # 頂部高光線
            if fill_width > 6:
                highlight_surf = pygame.Surface((fill_width - 6, 1), pygame.SRCALPHA)
                highlight_surf.fill((255, 255, 255, 60))
                screen.blit(highlight_surf, (self.rect.x + 3, self.rect.y + 2))

        # 邊框
        pygame.draw.rect(screen, self.border_color, self.rect, width=1, border_radius=8)

        # 完成光暈
        if self.progress >= 0.95:
            glow_intensity = 0.5 + 0.5 * math.sin(self.glow_phase)
            glow_rect = self.rect.inflate(4, 4)
            glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
            glow_alpha = int(30 * glow_intensity)
            glow_color = tuple(min(255, c + 50) for c in self.fill_color_end)
            pygame.draw.rect(glow_surf, (*glow_color, glow_alpha),
                           (0, 0, glow_rect.width, glow_rect.height), border_radius=10)
            screen.blit(glow_surf, glow_rect.topleft)

    def _draw_shine(self, screen: pygame.Surface, fill_width: int):
        """繪製光澤效果"""
        if self.shine_offset < 0 or self.shine_offset > 1.2:
            return

        shine_surf = pygame.Surface((fill_width, self.rect.height), pygame.SRCALPHA)
        shine_width = int(fill_width * 0.2)
        x_pos = int(self.shine_offset * (fill_width + shine_width) - shine_width)

        for i in range(shine_width):
            alpha = int(50 * (1 - abs(i - shine_width/2) / (shine_width/2)))
            x = x_pos + i
            if 0 <= x < fill_width:
                pygame.draw.line(shine_surf, (255, 255, 255, alpha), (x, 0), (x, self.rect.height))

        # 應用遮罩
        mask = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, self.rect.width, self.rect.height),
                        border_radius=8)
        clip = pygame.Surface((fill_width, self.rect.height), pygame.SRCALPHA)
        clip.blit(mask, (0, 0))
        shine_surf.blit(clip, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)

        screen.blit(shine_surf, self.rect.topleft)
