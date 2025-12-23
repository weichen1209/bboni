"""
裝置校正場景
"""

import pygame
import time
from .base import Scene, Button, ProgressBar
from ..config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, WHITE, GRAY, LIGHT_GRAY,
    PRIMARY_COLOR, SECONDARY_COLOR, ACCENT_COLOR,
    CALIBRATION_SAMPLES, CALIBRATION_DELAY, FontManager
)


class CalibrationScene(Scene):
    """裝置校正場景"""

    def __init__(self, game):
        super().__init__(game)

        # 狀態
        self.state = "waiting"  # waiting, calibrating, done
        self.calibration_progress = 0.0
        self.calibration_start_time = 0
        self.countdown = 3

        # UI 元件
        center_x = SCREEN_WIDTH // 2
        self.progress_bar = ProgressBar(
            center_x - 200, 400, 400, 30,
            fill_color=PRIMARY_COLOR
        )
        self.start_button = Button(
            center_x - 100, 500, 200, 50,
            "開始", PRIMARY_COLOR
        )
        self.skip_button = Button(
            center_x - 100, 570, 200, 50,
            "跳過", GRAY
        )

    def on_enter(self):
        """進入場景"""
        self.state = "waiting"
        self.calibration_progress = 0.0

    def handle_event(self, event: pygame.event.Event):
        """處理事件"""
        if self.state == "waiting":
            if self.start_button.handle_event(event):
                self._start_calibration()

            if self.skip_button.handle_event(event):
                self.switch_to("menu")

        elif self.state == "done":
            if event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                self.switch_to("intro1")

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.switch_to("menu")
            elif event.key == pygame.K_SPACE or event.key == pygame.K_RETURN:
                if self.state == "waiting":
                    self._start_calibration()
                elif self.state == "done":
                    self.switch_to("intro1")

    def _start_calibration(self):
        """開始校正"""
        self.state = "calibrating"
        self.calibration_start_time = time.time()
        self.calibration_progress = 0.0

    def update(self, dt: float):
        """更新"""
        # 更新進度條動畫
        self.progress_bar.update(dt)

        if self.state == "calibrating":
            elapsed = time.time() - self.calibration_start_time
            total_time = CALIBRATION_SAMPLES * CALIBRATION_DELAY + 1.0

            self.calibration_progress = min(elapsed / total_time, 1.0)
            self.progress_bar.set_progress(self.calibration_progress)

            if self.calibration_progress >= 1.0:
                # 執行校正
                if self.game.sensor and self.game.sensor.is_connected:
                    self.game.sensor.calibrate(
                        samples=CALIBRATION_SAMPLES,
                        delay=CALIBRATION_DELAY
                    )
                self.state = "done"

    def draw(self, screen: pygame.Surface):
        """繪製"""
        # 背景
        screen.fill((30, 40, 60))

        # 取得字體
        title_font = FontManager.get_sized(40)
        text_font = FontManager.get('medium')

        # 標題（使用快取）
        title_surface = self.render_text(title_font, "裝置校正", WHITE)
        title_rect = title_surface.get_rect(center=(SCREEN_WIDTH // 2, 100))
        screen.blit(title_surface, title_rect)

        # bboni 裝置圖示
        self._draw_bboni_device(screen)

        if self.state == "waiting":
            # 說明文字（使用快取）
            instructions = [
                "請將 bboni AI 放置於平坦表面",
                "校正期間請保持裝置靜止",
                "這將需要約 2 秒鐘"
            ]
            for i, text in enumerate(instructions):
                text_surface = self.render_text(text_font, text, LIGHT_GRAY)
                text_rect = text_surface.get_rect(center=(SCREEN_WIDTH // 2, 300 + i * 40))
                screen.blit(text_surface, text_rect)

            # 按鈕
            self.start_button.draw(screen)
            self.skip_button.draw(screen)

        elif self.state == "calibrating":
            # 校正中（使用快取）
            status_surface = self.render_text(title_font, "校正中...", ACCENT_COLOR)
            status_rect = status_surface.get_rect(center=(SCREEN_WIDTH // 2, 320))
            screen.blit(status_surface, status_rect)

            hint_surface = self.render_text(text_font, "請保持裝置靜止！", WHITE)
            hint_rect = hint_surface.get_rect(center=(SCREEN_WIDTH // 2, 370))
            screen.blit(hint_surface, hint_rect)

            # 進度條
            self.progress_bar.draw(screen)

            # 百分比（會變化，但數量有限可以快取）
            percent_text = f"{int(self.calibration_progress * 100)}%"
            percent_surface = self.render_text(text_font, percent_text, WHITE)
            percent_rect = percent_surface.get_rect(center=(SCREEN_WIDTH // 2, 460))
            screen.blit(percent_surface, percent_rect)

        elif self.state == "done":
            # 完成（使用快取）
            done_surface = self.render_text(title_font, "校正完成！", SECONDARY_COLOR)
            done_rect = done_surface.get_rect(center=(SCREEN_WIDTH // 2, 350))
            screen.blit(done_surface, done_rect)

            hint_surface = self.render_text(text_font, "按任意鍵繼續", LIGHT_GRAY)
            hint_rect = hint_surface.get_rect(center=(SCREEN_WIDTH // 2, 450))
            screen.blit(hint_surface, hint_rect)

    def _draw_bboni_device(self, screen: pygame.Surface):
        """繪製 bboni 裝置圖示"""
        center_x = SCREEN_WIDTH // 2
        center_y = 200

        # 裝置外框
        device_rect = pygame.Rect(center_x - 40, center_y - 40, 80, 80)
        pygame.draw.rect(screen, (40, 40, 40), device_rect, border_radius=15)
        pygame.draw.rect(screen, (60, 60, 60), device_rect, width=2, border_radius=15)

        # LED 指示燈
        led_color = SECONDARY_COLOR if self.state != "calibrating" else ACCENT_COLOR
        pygame.draw.circle(screen, led_color, (center_x + 25, center_y - 25), 5)

        # 裝置標誌（使用快取）
        logo_font = FontManager.get_sized(16)
        logo_surface = self.render_text(logo_font, "bboni", WHITE)
        logo_rect = logo_surface.get_rect(center=(center_x, center_y))
        screen.blit(logo_surface, logo_rect)

        # 桌面
        if self.state != "done":
            pygame.draw.rect(
                screen, (80, 60, 40),
                (center_x - 100, center_y + 50, 200, 20),
                border_radius=3
            )
