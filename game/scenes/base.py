"""
場景基礎類別
"""

import pygame
from abc import ABC, abstractmethod
from ..utils.drawing import create_gradient_surface
from ..config import SCREEN_WIDTH, SCREEN_HEIGHT


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
        pass

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

    def render_text(self, font: pygame.font.Font, text: str, color: tuple) -> pygame.Surface:
        """渲染文字（帶快取）"""
        cache_key = (id(font), text, color)
        if not hasattr(self, '_text_cache'):
            self._text_cache = {}
        if cache_key not in self._text_cache:
            self._text_cache[cache_key] = font.render(text, True, color)
        return self._text_cache[cache_key]


class Button:
    """簡易按鈕類別"""

    def __init__(self, x: int, y: int, width: int, height: int,
                 text: str, color=(52, 152, 219), hover_color=(41, 128, 185),
                 text_color=(255, 255, 255), font_size: int = 32):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.text_color = text_color
        self.font_size = font_size
        self.is_hovered = False
        self._font = None

    @property
    def font(self):
        if self._font is None:
            self._font = pygame.font.SysFont("Microsoft JhengHei", self.font_size)
        return self._font

    def handle_event(self, event: pygame.event.Event) -> bool:
        """處理事件，返回是否被點擊"""
        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1 and self.rect.collidepoint(event.pos):
                return True
        return False

    def draw(self, screen: pygame.Surface):
        """繪製按鈕"""
        color = self.hover_color if self.is_hovered else self.color

        # 繪製圓角矩形
        pygame.draw.rect(screen, color, self.rect, border_radius=10)

        # 繪製文字
        text_surface = self.font.render(self.text, True, self.text_color)
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)


class ProgressBar:
    """進度條類別"""

    def __init__(self, x: int, y: int, width: int, height: int,
                 bg_color=(200, 200, 200), fill_color=(52, 152, 219),
                 border_color=(100, 100, 100)):
        self.rect = pygame.Rect(x, y, width, height)
        self.bg_color = bg_color
        self.fill_color = fill_color
        self.border_color = border_color
        self.progress = 0.0  # 0.0 ~ 1.0

    def set_progress(self, value: float):
        """設定進度 (0.0 ~ 1.0)"""
        self.progress = max(0.0, min(1.0, value))

    def draw(self, screen: pygame.Surface):
        """繪製進度條"""
        # 背景
        pygame.draw.rect(screen, self.bg_color, self.rect, border_radius=5)

        # 填充
        if self.progress > 0:
            fill_width = int(self.rect.width * self.progress)
            fill_rect = pygame.Rect(
                self.rect.x, self.rect.y,
                fill_width, self.rect.height
            )
            pygame.draw.rect(screen, self.fill_color, fill_rect, border_radius=5)

        # 邊框
        pygame.draw.rect(screen, self.border_color, self.rect, width=2, border_radius=5)
