"""
暱稱輸入場景
"""

import pygame
from .base import Scene, Button, TextInput
from ..config import *


class NicknameScene(Scene):
    """暱稱輸入場景"""

    def __init__(self, game):
        super().__init__(game)

        center_x = SCREEN_WIDTH // 2

        # 文字輸入框
        self.nickname_input = TextInput(
            center_x - 200, 300, 400, 60,
            placeholder="輸入暱稱...",
            max_length=12,
            font_size=28
        )

        # 按鈕
        self.continue_button = Button(
            center_x - 220, 450, 200, 55,
            "繼續", PRIMARY_COLOR
        )
        self.back_button = Button(
            center_x + 20, 450, 200, 55,
            "返回", GRAY
        )

        # 字體
        self.title_font = None
        self.text_font = None
        self.hint_font = None

    def on_enter(self):
        """進入場景"""
        # 初始化字體
        self.title_font = pygame.font.SysFont("Microsoft JhengHei", 42)
        self.text_font = pygame.font.SysFont("Microsoft JhengHei", 24)
        self.hint_font = pygame.font.SysFont("Microsoft JhengHei", 18)

        # 預繪製漸層背景
        self._gradient_surface = self.create_gradient_background((60, 90, 120), factor=0.4)

        # 恢復之前的暱稱（如果有）
        if hasattr(self.game, 'player_nickname') and self.game.player_nickname:
            self.nickname_input.set_text(self.game.player_nickname)

        # 啟用文字輸入模式
        pygame.key.start_text_input()

    def on_exit(self):
        """離開場景"""
        pygame.key.stop_text_input()

    def handle_event(self, event: pygame.event.Event):
        """處理事件"""
        # 處理文字輸入
        if self.nickname_input.handle_event(event):
            self._on_continue()

        # 處理按鈕
        if self.continue_button.handle_event(event):
            self._on_continue()

        if self.back_button.handle_event(event):
            self.switch_to("menu")

        # 鍵盤快捷鍵
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.switch_to("menu")

    def _on_continue(self):
        """繼續按鈕處理"""
        nickname = self.nickname_input.get_text().strip()
        if nickname:
            self.game.player_nickname = nickname
            self.switch_to("calibration")

    def update(self, dt: float):
        """更新"""
        self.nickname_input.update(dt)
        self.continue_button.update(dt)
        self.back_button.update(dt)

    def draw(self, screen: pygame.Surface):
        """繪製"""
        # 背景
        screen.blit(self._gradient_surface, (0, 0))

        center_x = SCREEN_WIDTH // 2

        # 標題
        title_text = self.title_font.render("輸入您的暱稱", True, WHITE)
        title_rect = title_text.get_rect(center=(center_x, 150))
        screen.blit(title_text, title_rect)

        # 副標題說明
        subtitle_text = self.text_font.render(
            "暱稱將顯示在排行榜上", True, LIGHT_GRAY
        )
        subtitle_rect = subtitle_text.get_rect(center=(center_x, 210))
        screen.blit(subtitle_text, subtitle_rect)

        # 輸入框
        self.nickname_input.draw(screen)

        # 字數統計
        current_len = len(self.nickname_input.get_text())
        max_len = self.nickname_input.max_length
        count_color = ACCENT_COLOR if current_len >= max_len else TEXT_MUTED
        count_text = self.hint_font.render(f"{current_len}/{max_len}", True, count_color)
        count_rect = count_text.get_rect(center=(center_x, 380))
        screen.blit(count_text, count_rect)

        # 按鈕
        self.continue_button.draw(screen)
        self.back_button.draw(screen)

        # 提示
        hint_text = self.hint_font.render(
            "按 Enter 繼續，ESC 返回", True, GRAY
        )
        hint_rect = hint_text.get_rect(center=(center_x, 550))
        screen.blit(hint_text, hint_rect)

        # 裝飾：晶圓圖案
        self._draw_decoration(screen)

    def _draw_decoration(self, screen: pygame.Surface):
        """繪製裝飾元素"""
        # 左側小晶圓
        pygame.draw.circle(screen, (40, 50, 70), (80, SCREEN_HEIGHT - 100), 60)
        pygame.draw.circle(screen, SILICON_BLUE, (80, SCREEN_HEIGHT - 100), 55)
        for i in range(-2, 3):
            for j in range(-2, 3):
                if i*i + j*j <= 4:
                    pygame.draw.rect(
                        screen, (60, 120, 160),
                        (80 + i*18 - 7, SCREEN_HEIGHT - 100 + j*18 - 7, 14, 14)
                    )

        # 右側小晶圓
        pygame.draw.circle(screen, (40, 50, 70), (SCREEN_WIDTH - 80, SCREEN_HEIGHT - 100), 60)
        pygame.draw.circle(screen, SILICON_BLUE, (SCREEN_WIDTH - 80, SCREEN_HEIGHT - 100), 55)
        for i in range(-2, 3):
            for j in range(-2, 3):
                if i*i + j*j <= 4:
                    color_idx = (i + j + 4) % len(WAFER_RAINBOW)
                    pygame.draw.rect(
                        screen, WAFER_RAINBOW[color_idx],
                        (SCREEN_WIDTH - 80 + i*18 - 7, SCREEN_HEIGHT - 100 + j*18 - 7, 14, 14)
                    )
