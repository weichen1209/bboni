"""
主選單場景
"""

import pygame
from .base import Scene, Button
from ..config import *


class MenuScene(Scene):
    """主選單場景"""

    def __init__(self, game):
        super().__init__(game)

        # 按鈕
        center_x = SCREEN_WIDTH // 2
        self.start_button = Button(
            center_x - 150, 360, 300, 60,
            "開始遊戲", PRIMARY_COLOR
        )
        self.leaderboard_button = Button(
            center_x - 150, 440, 300, 60,
            "排行榜", SECONDARY_COLOR
        )
        self.quit_button = Button(
            center_x - 150, 520, 300, 60,
            "離開", DANGER_COLOR
        )

        # 標題字體
        self.title_font = None
        self.subtitle_font = None

        # 連接狀態
        self.connection_status = "Disconnected"

    def on_enter(self):
        """進入場景"""
        # 初始化字體
        self.title_font = pygame.font.SysFont("Microsoft JhengHei", 48)
        self.subtitle_font = pygame.font.SysFont("Microsoft JhengHei", 28)

        # 預繪製漸層背景（效能優化）
        self._gradient_surface = self.create_gradient_background((80, 100, 130), factor=0.4)

        # 檢查感測器連接
        if self.game.sensor and self.game.sensor.is_connected:
            self.connection_status = "bboni AI 已連接"
        else:
            self.connection_status = "bboni AI: 連接中..."

    def handle_event(self, event: pygame.event.Event):
        """處理事件"""
        if self.start_button.handle_event(event):
            # 開始遊戲 - 進入暱稱輸入場景
            self.switch_to("nickname")

        if self.leaderboard_button.handle_event(event):
            # 查看排行榜
            self.switch_to("leaderboard")

        if self.quit_button.handle_event(event):
            # 退出遊戲
            pygame.event.post(pygame.event.Event(pygame.QUIT))

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                self.switch_to("nickname")
            elif event.key == pygame.K_SPACE:
                self.switch_to("leaderboard")
            elif event.key == pygame.K_ESCAPE:
                pygame.event.post(pygame.event.Event(pygame.QUIT))

    def update(self, dt: float):
        """更新"""
        # 更新連接狀態
        if self.game.sensor:
            if self.game.sensor.is_connected:
                self.connection_status = "bboni AI Connected"
            else:
                self.connection_status = "bboni AI: Connecting..."

        # 更新按鈕動畫
        self.start_button.update(dt)
        self.leaderboard_button.update(dt)
        self.quit_button.update(dt)

    def draw(self, screen: pygame.Surface):
        """繪製"""
        # 背景漸層（使用預繪製的快取）
        screen.blit(self._gradient_surface, (0, 0))

        # 裝飾：晶圓圖案
        self._draw_wafer_decoration(screen)

        # 標題
        title_text = self.title_font.render("晶圓工程師", True, WHITE)
        title_rect = title_text.get_rect(center=(SCREEN_WIDTH // 2, 150))
        screen.blit(title_text, title_rect)

        # 中文副標題
        subtitle_text = self.subtitle_font.render(
            "互動式半導體科普遊戲", True, LIGHT_GRAY
        )
        subtitle_rect = subtitle_text.get_rect(center=(SCREEN_WIDTH // 2, 220))
        screen.blit(subtitle_text, subtitle_rect)

        # 連接狀態
        status_color = SECONDARY_COLOR if "已連接" in self.connection_status else ACCENT_COLOR
        status_text = self.subtitle_font.render(self.connection_status, True, status_color)
        status_rect = status_text.get_rect(center=(SCREEN_WIDTH // 2, 300))
        screen.blit(status_text, status_rect)

        # 按鈕
        self.start_button.draw(screen)
        self.leaderboard_button.draw(screen)
        self.quit_button.draw(screen)

        # 說明
        hint_font = pygame.font.SysFont("Microsoft JhengHei", 18)
        hint_text = hint_font.render(
            "按 ENTER 開始，SPACE 排行榜，ESC 離開", True, GRAY
        )
        hint_rect = hint_text.get_rect(center=(SCREEN_WIDTH // 2, 600))
        screen.blit(hint_text, hint_rect)

        # 版本資訊
        version_text = hint_font.render("v1.0 - AI 創新競賽", True, DARK_GRAY)
        version_rect = version_text.get_rect(bottomright=(SCREEN_WIDTH - 20, SCREEN_HEIGHT - 20))
        screen.blit(version_text, version_rect)

    def _draw_wafer_decoration(self, screen: pygame.Surface):
        """繪製晶圓裝飾"""
        # 左側晶圓
        pygame.draw.circle(screen, (50, 60, 80), (100, 400), 80)
        pygame.draw.circle(screen, SILICON_BLUE, (100, 400), 75)
        # 晶圓網格
        for i in range(-3, 4):
            for j in range(-3, 4):
                if i*i + j*j <= 9:
                    pygame.draw.rect(
                        screen, (60, 120, 160),
                        (100 + i*20 - 8, 400 + j*20 - 8, 16, 16)
                    )

        # 右側晶圓
        pygame.draw.circle(screen, (50, 60, 80), (SCREEN_WIDTH - 100, 400), 80)
        pygame.draw.circle(screen, SILICON_BLUE, (SCREEN_WIDTH - 100, 400), 75)
        for i in range(-3, 4):
            for j in range(-3, 4):
                if i*i + j*j <= 9:
                    color_idx = (i + j + 6) % len(WAFER_RAINBOW)
                    pygame.draw.rect(
                        screen, WAFER_RAINBOW[color_idx],
                        (SCREEN_WIDTH - 100 + i*20 - 8, 400 + j*20 - 8, 16, 16)
                    )
