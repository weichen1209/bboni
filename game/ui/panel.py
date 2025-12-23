"""
面板元件
帶毛玻璃效果的容器
"""

import pygame
from ..config import (
    BG_MEDIUM, BG_LIGHT, WHITE, GRAY,
    PANEL_CORNER_RADIUS, TEXT_PRIMARY
)


class Panel:
    """面板容器"""

    def __init__(self, x: int, y: int, width: int, height: int,
                 title: str = None,
                 bg_color: tuple = BG_MEDIUM,
                 border_color: tuple = None,
                 alpha: int = 220,
                 show_header: bool = True):
        """
        初始化面板

        Args:
            x, y: 位置
            width, height: 尺寸
            title: 標題文字
            bg_color: 背景顏色
            border_color: 邊框顏色
            alpha: 透明度 (0-255)
            show_header: 是否顯示標題列
        """
        self.rect = pygame.Rect(x, y, width, height)
        self.title = title
        self.bg_color = bg_color
        self.border_color = border_color or tuple(min(255, c + 30) for c in bg_color)
        self.alpha = alpha
        self.show_header = show_header and title

        self.header_height = 40 if self.show_header else 0

        # 字體
        self._title_font = None
        self._cached_surface = None

    @property
    def title_font(self):
        if self._title_font is None:
            self._title_font = pygame.font.SysFont("Microsoft JhengHei", 20)
        return self._title_font

    @property
    def content_rect(self) -> pygame.Rect:
        """取得內容區域（排除標題列）"""
        return pygame.Rect(
            self.rect.x + 10,
            self.rect.y + self.header_height + 10,
            self.rect.width - 20,
            self.rect.height - self.header_height - 20
        )

    def draw(self, screen: pygame.Surface):
        """繪製面板"""
        # 主體
        self._draw_body(screen)

        # 標題列
        if self.show_header:
            self._draw_header(screen)

        # 邊框
        self._draw_border(screen)

        # 角落裝飾
        self._draw_corners(screen)

    def _draw_body(self, screen: pygame.Surface):
        """繪製主體"""
        body_surf = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)

        # 漸層背景
        for y in range(self.rect.height):
            ratio = y / self.rect.height
            brightness = 1.0 + ratio * 0.15
            row_color = tuple(min(255, int(c * brightness)) for c in self.bg_color)
            row_alpha = int(self.alpha * (0.9 + ratio * 0.1))
            pygame.draw.line(body_surf, (*row_color, row_alpha),
                           (0, y), (self.rect.width, y))

        # 應用圓角
        mask_surf = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        pygame.draw.rect(mask_surf, (255, 255, 255, 255),
                        (0, 0, self.rect.width, self.rect.height),
                        border_radius=PANEL_CORNER_RADIUS)
        body_surf.blit(mask_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)

        screen.blit(body_surf, self.rect.topleft)

    def _draw_header(self, screen: pygame.Surface):
        """繪製標題列"""
        header_rect = pygame.Rect(
            self.rect.x, self.rect.y,
            self.rect.width, self.header_height
        )

        # 標題列背景（稍微深一點）
        header_surf = pygame.Surface((header_rect.width, header_rect.height), pygame.SRCALPHA)
        header_color = tuple(max(0, c - 15) for c in self.bg_color)
        pygame.draw.rect(header_surf, (*header_color, self.alpha),
                        (0, 0, header_rect.width, header_rect.height),
                        border_top_left_radius=PANEL_CORNER_RADIUS,
                        border_top_right_radius=PANEL_CORNER_RADIUS)

        screen.blit(header_surf, header_rect.topleft)

        # 標題文字
        if self.title:
            title_surface = self.title_font.render(self.title, True, TEXT_PRIMARY)
            title_rect = title_surface.get_rect(
                midleft=(header_rect.x + 15, header_rect.centery)
            )
            screen.blit(title_surface, title_rect)

        # 分隔線
        line_y = header_rect.bottom
        pygame.draw.line(screen, self.border_color,
                        (self.rect.x + 10, line_y),
                        (self.rect.right - 10, line_y), 1)

    def _draw_border(self, screen: pygame.Surface):
        """繪製邊框"""
        pygame.draw.rect(screen, self.border_color, self.rect,
                        width=1, border_radius=PANEL_CORNER_RADIUS)

    def _draw_corners(self, screen: pygame.Surface):
        """繪製角落裝飾"""
        corner_size = 8
        corner_color = self.border_color

        # 四個角落的 L 形裝飾
        corners = [
            (self.rect.topleft, (1, 1)),      # 左上
            (self.rect.topright, (-1, 1)),    # 右上
            (self.rect.bottomleft, (1, -1)),  # 左下
            (self.rect.bottomright, (-1, -1)) # 右下
        ]

        for (cx, cy), (dx, dy) in corners:
            # 調整起點位置
            if dx > 0:
                sx = cx + 3
            else:
                sx = cx - 3
            if dy > 0:
                sy = cy + 3
            else:
                sy = cy - 3

            # 繪製 L 形
            pygame.draw.line(screen, corner_color,
                           (sx, sy), (sx + dx * corner_size, sy), 2)
            pygame.draw.line(screen, corner_color,
                           (sx, sy), (sx, sy + dy * corner_size), 2)


class GlassPanel(Panel):
    """毛玻璃面板（更強的透明效果）"""

    def __init__(self, x: int, y: int, width: int, height: int,
                 title: str = None,
                 tint_color: tuple = (100, 150, 200),
                 alpha: int = 180):
        super().__init__(x, y, width, height, title, tint_color, alpha=alpha)

    def _draw_body(self, screen: pygame.Surface):
        """繪製毛玻璃效果主體"""
        body_surf = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)

        # 基礎半透明填充
        base_alpha = int(self.alpha * 0.7)
        pygame.draw.rect(body_surf, (*self.bg_color, base_alpha),
                        (0, 0, self.rect.width, self.rect.height),
                        border_radius=PANEL_CORNER_RADIUS)

        # 添加內部光暈
        inner_rect = pygame.Rect(5, 5, self.rect.width - 10, self.rect.height - 10)
        inner_color = tuple(min(255, c + 20) for c in self.bg_color)
        pygame.draw.rect(body_surf, (*inner_color, base_alpha // 2),
                        inner_rect, border_radius=PANEL_CORNER_RADIUS - 3)

        # 頂部高光
        highlight_surf = pygame.Surface((self.rect.width - 20, 2), pygame.SRCALPHA)
        highlight_surf.fill((255, 255, 255, 40))
        body_surf.blit(highlight_surf, (10, 5))

        screen.blit(body_surf, self.rect.topleft)
