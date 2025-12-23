"""
增強版按鈕元件
帶陰影、漸層、hover動畫效果
"""

import pygame
import math
from ..config import (
    PRIMARY_COLOR, PRIMARY_LIGHT, PRIMARY_DARK,
    WHITE, BG_DARK, BG_SURFACE, TEXT_PRIMARY,
    BUTTON_CORNER_RADIUS, BUTTON_SHADOW_OFFSET,
    ANIMATION_FAST, GLOW_BLUE
)
from ..utils.animations import lerp, lerp_color, ease_out_quad


class EnhancedButton:
    """增強版按鈕"""

    def __init__(self, x: int, y: int, width: int, height: int,
                 text: str,
                 color: tuple = PRIMARY_COLOR,
                 hover_color: tuple = PRIMARY_LIGHT,
                 text_color: tuple = TEXT_PRIMARY,
                 font_size: int = 28,
                 icon: str = None):
        """
        初始化按鈕

        Args:
            x, y: 位置
            width, height: 尺寸
            text: 按鈕文字
            color: 主色
            hover_color: hover 時的顏色
            text_color: 文字顏色
            font_size: 字體大小
            icon: 可選的圖標文字
        """
        self.base_rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.text_color = text_color
        self.font_size = font_size
        self.icon = icon

        # 狀態
        self.is_hovered = False
        self.is_pressed = False
        self.is_enabled = True

        # 動畫狀態
        self.hover_progress = 0.0      # 0 = idle, 1 = hover
        self.press_progress = 0.0      # 0 = normal, 1 = pressed
        self.glow_intensity = 0.0      # 光暈強度
        self.shimmer_offset = 0.0      # 光澤偏移

        # 快取
        self._font = None
        self._shadow_surface = None
        self._glow_surface = None

    @property
    def font(self):
        if self._font is None:
            self._font = pygame.font.SysFont("Microsoft JhengHei", self.font_size)
        return self._font

    @property
    def rect(self):
        """取得當前矩形（考慮縮放）"""
        scale = 1.0 + self.hover_progress * 0.02 - self.press_progress * 0.04
        new_width = int(self.base_rect.width * scale)
        new_height = int(self.base_rect.height * scale)
        new_x = self.base_rect.centerx - new_width // 2
        new_y = self.base_rect.centery - new_height // 2
        return pygame.Rect(new_x, new_y, new_width, new_height)

    def handle_event(self, event: pygame.event.Event) -> bool:
        """處理事件，返回是否被點擊"""
        if not self.is_enabled:
            return False

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
        target_hover = 1.0 if self.is_hovered else 0.0
        self.hover_progress += (target_hover - self.hover_progress) * min(1.0, dt / ANIMATION_FAST)

        # Press 動畫
        target_press = 1.0 if self.is_pressed else 0.0
        self.press_progress += (target_press - self.press_progress) * min(1.0, dt / 0.08)

        # 光暈動畫
        self.glow_intensity = self.hover_progress * (0.7 + 0.3 * math.sin(pygame.time.get_ticks() / 300))

        # 光澤動畫
        self.shimmer_offset += dt * 0.5
        if self.shimmer_offset > 2.0:
            self.shimmer_offset = -0.5

    def draw(self, screen: pygame.Surface):
        """繪製按鈕"""
        rect = self.rect

        # 1. 繪製陰影
        self._draw_shadow(screen, rect)

        # 2. 繪製光暈（hover 時）
        if self.glow_intensity > 0.01:
            self._draw_glow(screen, rect)

        # 3. 繪製主體
        self._draw_body(screen, rect)

        # 4. 繪製光澤效果
        if self.is_hovered:
            self._draw_shimmer(screen, rect)

        # 5. 繪製文字
        self._draw_text(screen, rect)

    def _draw_shadow(self, screen: pygame.Surface, rect: pygame.Rect):
        """繪製陰影"""
        shadow_rect = rect.copy()
        shadow_rect.x += BUTTON_SHADOW_OFFSET[0]
        shadow_rect.y += BUTTON_SHADOW_OFFSET[1]

        # 使用多層陰影增加模糊效果
        for i in range(3):
            alpha = 30 - i * 10
            offset = i * 2
            s_rect = shadow_rect.inflate(offset, offset)
            s_rect.x += offset // 2
            s_rect.y += offset // 2

            shadow_surf = pygame.Surface((s_rect.width, s_rect.height), pygame.SRCALPHA)
            pygame.draw.rect(shadow_surf, (0, 0, 0, alpha),
                           (0, 0, s_rect.width, s_rect.height),
                           border_radius=BUTTON_CORNER_RADIUS + i)
            screen.blit(shadow_surf, s_rect.topleft)

    def _draw_glow(self, screen: pygame.Surface, rect: pygame.Rect):
        """繪製光暈"""
        glow_size = 15
        glow_rect = rect.inflate(glow_size * 2, glow_size * 2)

        glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)

        # 多層光暈
        for i in range(3):
            alpha = int(40 * self.glow_intensity * (3 - i) / 3)
            inflate = i * 5
            inner_rect = pygame.Rect(glow_size - inflate, glow_size - inflate,
                                    rect.width + inflate * 2, rect.height + inflate * 2)
            glow_color = (*GLOW_BLUE, alpha)
            pygame.draw.rect(glow_surf, glow_color, inner_rect,
                           border_radius=BUTTON_CORNER_RADIUS + inflate)

        screen.blit(glow_surf, glow_rect.topleft)

    def _draw_body(self, screen: pygame.Surface, rect: pygame.Rect):
        """繪製按鈕主體"""
        # 計算當前顏色
        current_color = lerp_color(self.color, self.hover_color, self.hover_progress)

        if not self.is_enabled:
            current_color = tuple(c // 2 for c in current_color)

        # 繪製漸層背景
        body_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)

        # 上半部較亮，下半部較暗
        for y in range(rect.height):
            ratio = y / rect.height
            # 上方較亮
            brightness = 1.1 - ratio * 0.2
            row_color = tuple(min(255, int(c * brightness)) for c in current_color)
            pygame.draw.line(body_surf, (*row_color, 255), (0, y), (rect.width, y))

        # 應用圓角遮罩
        mask_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(mask_surf, (255, 255, 255, 255),
                        (0, 0, rect.width, rect.height),
                        border_radius=BUTTON_CORNER_RADIUS)

        # 合併
        body_surf.blit(mask_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        screen.blit(body_surf, rect.topleft)

        # 繪製邊框
        border_color = lerp_color(current_color, WHITE, 0.3)
        pygame.draw.rect(screen, border_color, rect, width=2,
                        border_radius=BUTTON_CORNER_RADIUS)

    def _draw_shimmer(self, screen: pygame.Surface, rect: pygame.Rect):
        """繪製光澤效果"""
        if self.shimmer_offset < 0 or self.shimmer_offset > 1.5:
            return

        shimmer_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)

        # 對角線光澤
        shimmer_width = rect.width * 0.3
        x_pos = int(self.shimmer_offset * (rect.width + shimmer_width) - shimmer_width)

        for i in range(int(shimmer_width)):
            alpha = int(60 * (1 - abs(i - shimmer_width/2) / (shimmer_width/2)))
            x = x_pos + i
            if 0 <= x < rect.width:
                pygame.draw.line(shimmer_surf, (255, 255, 255, alpha),
                               (x, 0), (x, rect.height))

        # 應用圓角遮罩
        mask_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(mask_surf, (255, 255, 255, 255),
                        (0, 0, rect.width, rect.height),
                        border_radius=BUTTON_CORNER_RADIUS)
        shimmer_surf.blit(mask_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)

        screen.blit(shimmer_surf, rect.topleft)

    def _draw_text(self, screen: pygame.Surface, rect: pygame.Rect):
        """繪製文字"""
        text_color = self.text_color if self.is_enabled else tuple(c // 2 for c in self.text_color)

        # 渲染文字
        text_surface = self.font.render(self.text, True, text_color)
        text_rect = text_surface.get_rect(center=rect.center)

        # 按壓時稍微下移
        if self.is_pressed:
            text_rect.y += 2

        screen.blit(text_surface, text_rect)

    def set_enabled(self, enabled: bool):
        """設定啟用狀態"""
        self.is_enabled = enabled
