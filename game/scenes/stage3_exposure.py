"""
第三關：曝光顯影
玩家需要保持感測器穩定，模擬光刻機曝光過程
穩定度越高，曝光品質越好
"""

import pygame
import math
from collections import deque
from .base import Scene, Button, ProgressBar
from ..config import *


class ExposureStage(Scene):
    """曝光顯影關卡 - 保持穩定"""

    # 遊戲階段
    PHASE_INSTRUCTIONS = 0
    PHASE_EXPOSURE = 1
    PHASE_RESULT = 2

    # 曝光參數
    EXPOSURE_DURATION = 10.0      # 最長曝光時間 (秒)
    STABILITY_THRESHOLD = 0.85    # 穩定閾值 (低於此值顯示警告，非常嚴格)
    FILL_SPEED_STABLE = 0.15      # 穩定時進度填充速度
    FILL_SPEED_UNSTABLE = 0.02    # 不穩定時進度填充速度

    def __init__(self, game):
        super().__init__(game)

        # 遊戲階段
        self.phase = self.PHASE_INSTRUCTIONS

        # 曝光狀態
        self.exposure_elapsed = 0.0
        self.exposure_progress = 0.0     # 曝光進度 (0-1)
        self.stability_samples = []      # 穩定度樣本
        self.current_stability = 0.0

        # 動畫
        self.uv_pulse = 0.0              # UV 光脈動動畫
        self.warning_flash = 0.0         # 警告閃爍
        self.particle_angle = 0.0

        # 分數
        self.exposure_score = 0

        # UI 元件
        center_x = SCREEN_WIDTH // 2
        self.start_button = Button(
            center_x - 100, 550, 200, 50,
            "開始曝光", PRIMARY_COLOR
        )
        self.next_button = Button(
            center_x - 100, 620, 200, 50,
            "繼續", PRIMARY_COLOR
        )
        self.progress_bar = ProgressBar(
            center_x - 250, 580, 500, 30,
            bg_color=DARK_GRAY,
            fill_color=PHOTORESIST_PURPLE,
            border_color=GRAY
        )
        self.stability_bar = ProgressBar(
            center_x - 150, 520, 300, 20,
            bg_color=DARK_GRAY,
            fill_color=SECONDARY_COLOR,
            border_color=GRAY
        )

        # 字體
        self.title_font = None
        self.text_font = None
        self.small_font = None
        self.score_font = None

    def on_enter(self):
        """進入場景"""
        self.title_font = pygame.font.SysFont("Microsoft JhengHei", 36)
        self.text_font = pygame.font.SysFont("Microsoft JhengHei", 24)
        self.small_font = pygame.font.SysFont("Microsoft JhengHei", 18)
        self.score_font = pygame.font.SysFont("Microsoft JhengHei", 48)

        # 預繪製漸層背景（效能優化）
        self._bg_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        for y in range(SCREEN_HEIGHT):
            ratio = y / SCREEN_HEIGHT
            r = int(20 + (PHOTORESIST_PURPLE[0] - 20) * ratio * 0.15)
            g = int(10 + ratio * 10)
            b = int(40 + (PHOTORESIST_PURPLE[2] - 40) * ratio * 0.2)
            pygame.draw.line(self._bg_surface, (r, g, b), (0, y), (SCREEN_WIDTH, y))

        # 重置狀態
        self.phase = self.PHASE_INSTRUCTIONS
        self.exposure_elapsed = 0.0
        self.exposure_progress = 0.0
        self.stability_samples = []
        self.current_stability = 0.0
        self.exposure_score = 0
        self.uv_pulse = 0.0
        self.warning_flash = 0.0

    def handle_event(self, event: pygame.event.Event):
        """處理事件"""
        if self.phase == self.PHASE_INSTRUCTIONS:
            self._handle_instructions_event(event)
        elif self.phase == self.PHASE_EXPOSURE:
            self._handle_exposure_event(event)
        elif self.phase == self.PHASE_RESULT:
            self._handle_result_event(event)

        # ESC 返回選單
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.switch_to("menu")

    def _handle_instructions_event(self, event: pygame.event.Event):
        """指示階段事件處理"""
        if self.start_button.handle_event(event):
            self._start_exposure()

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE or event.key == pygame.K_RETURN:
                self._start_exposure()

    def _handle_exposure_event(self, event: pygame.event.Event):
        """曝光階段事件處理"""
        pass  # 曝光期間不需要特別事件處理

    def _handle_result_event(self, event: pygame.event.Event):
        """結果階段事件處理"""
        if self.next_button.handle_event(event):
            self._finish_stage()

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE or event.key == pygame.K_RETURN:
                self._finish_stage()

    def _start_exposure(self):
        """開始曝光階段"""
        self.phase = self.PHASE_EXPOSURE
        self.exposure_elapsed = 0.0
        self.exposure_progress = 0.0
        self.stability_samples = []

    def _finish_exposure(self):
        """完成曝光，進入結果階段"""
        self.exposure_score = self._calculate_score()
        self.game.scores["exposure"] = self.exposure_score
        self.phase = self.PHASE_RESULT

    def _finish_stage(self):
        """完成關卡，進入下一關"""
        # 檢查 stage4 是否存在，否則進入 result
        if "stage4" in self.game.scenes:
            self.switch_to("stage4")
        else:
            self.switch_to("result")

    def _get_stability(self) -> float:
        """取得穩定度（使用3軸加速度計算整體穩定性）"""
        if self.game.sensor and self.game.sensor.is_connected:
            data = self.game.sensor.get_imu_data()
            # 計算3軸加速度向量的大小 (靈敏度: 2048 LSB/g，靜止時約為 2048)
            # 注意：靜止時 az 約為 2048 (1g)，ax/ay 約為 0
            total_accel = (data.ax ** 2 + data.ay ** 2 + data.az ** 2) ** 0.5
            # 靜止時 total_accel 約為 2048 (1g)
            # 計算偏離靜止狀態的程度
            deviation = abs(total_accel - 2048) / 2048.0
            # 當偏離超過 0.3g 時穩定度趨近 0
            stability = max(0.0, 1.0 - deviation / 0.3)
            return stability
        return 1.0  # 裝置未連接時視為穩定

    def _calculate_score(self) -> int:
        """計算曝光品質分數"""
        if len(self.stability_samples) < 10:
            return 50  # 樣本不足給基本分

        # 計算平均穩定度
        avg_stability = sum(self.stability_samples) / len(self.stability_samples)

        # 計算穩定度一致性（標準差越小越好）
        variance = sum((s - avg_stability) ** 2 for s in self.stability_samples) / len(self.stability_samples)
        std_dev = variance ** 0.5

        # 基礎分數 = 平均穩定度 * 80
        base_score = avg_stability * 80

        # 一致性獎勵 = (1 - 標準差) * 20
        consistency_bonus = max(0, (1 - std_dev)) * 20

        total = int(base_score + consistency_bonus)
        return max(0, min(100, total))

    def update(self, dt: float):
        """更新遊戲邏輯"""
        # 更新動畫
        self.uv_pulse += dt * 5
        self.particle_angle += dt * 30

        if self.phase == self.PHASE_INSTRUCTIONS:
            pass  # 等待使用者開始
        elif self.phase == self.PHASE_EXPOSURE:
            self._update_exposure_phase(dt)
        elif self.phase == self.PHASE_RESULT:
            pass

    def _update_exposure_phase(self, dt: float):
        """曝光階段更新"""
        # 更新經過時間
        self.exposure_elapsed += dt

        # 取得當前穩定度
        self.current_stability = self._get_stability()
        self.stability_samples.append(self.current_stability)

        # 更新穩定度顯示條
        self.stability_bar.set_progress(self.current_stability)

        # 根據穩定度更新曝光進度
        if self.current_stability >= self.STABILITY_THRESHOLD:
            self.exposure_progress += self.FILL_SPEED_STABLE * dt
            self.warning_flash = max(0, self.warning_flash - dt * 3)
        else:
            self.exposure_progress += self.FILL_SPEED_UNSTABLE * dt
            self.warning_flash = min(1, self.warning_flash + dt * 5)

        # 更新進度條
        self.progress_bar.set_progress(self.exposure_progress)

        # 檢查是否完成
        if self.exposure_progress >= 1.0 or self.exposure_elapsed >= self.EXPOSURE_DURATION:
            self._finish_exposure()

    def draw(self, screen: pygame.Surface):
        """繪製場景"""
        self._draw_background(screen)

        if self.phase == self.PHASE_INSTRUCTIONS:
            self._draw_instructions(screen)
        elif self.phase == self.PHASE_EXPOSURE:
            self._draw_exposure_phase(screen)
        elif self.phase == self.PHASE_RESULT:
            self._draw_result(screen)

    def _draw_background(self, screen: pygame.Surface):
        """繪製漸層背景（使用預繪製的快取）"""
        screen.blit(self._bg_surface, (0, 0))

    def _draw_instructions(self, screen: pygame.Surface):
        """繪製指示畫面"""
        # 標題
        title = self.title_font.render("曝光顯影 - 保持穩定", True, WHITE)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 80))
        screen.blit(title, title_rect)

        # 晶圓預覽
        self._draw_wafer_preview(screen, SCREEN_WIDTH // 2, 280)

        # 說明文字
        instructions = [
            "保持裝置穩定，讓UV光均勻曝光晶圓",
            "穩定度越高，曝光進度越快",
            "晃動會降低曝光品質！"
        ]

        y_start = 420
        for i, text in enumerate(instructions):
            surface = self.text_font.render(text, True, LIGHT_GRAY)
            rect = surface.get_rect(center=(SCREEN_WIDTH // 2, y_start + i * 35))
            screen.blit(surface, rect)

        # 開始按鈕
        self.start_button.draw(screen)

    def _draw_exposure_phase(self, screen: pygame.Surface):
        """繪製曝光階段"""
        # 標題
        title = self.title_font.render("曝光中 - 保持穩定！", True, WHITE)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 40))
        screen.blit(title, title_rect)

        # UV 光效果
        self._draw_uv_light(screen)

        # 晶圓（曝光中）
        self._draw_wafer_exposing(screen, SCREEN_WIDTH // 2, 280)

        # 穩定度顯示
        stability_label = "穩定度："
        if self.current_stability >= self.STABILITY_THRESHOLD:
            stability_label += "良好"
            label_color = SECONDARY_COLOR
        else:
            stability_label += "不穩定！"
            label_color = DANGER_COLOR

        stability_text = self.text_font.render(stability_label, True, label_color)
        stability_rect = stability_text.get_rect(center=(SCREEN_WIDTH // 2, 490))
        screen.blit(stability_text, stability_rect)

        self.stability_bar.draw(screen)

        # 警告效果
        if self.warning_flash > 0:
            warning_alpha = int(150 * self.warning_flash * (0.5 + 0.5 * math.sin(self.uv_pulse * 3)))
            warning_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            warning_surf.fill((255, 0, 0, warning_alpha))
            screen.blit(warning_surf, (0, 0))

            warning_text = self.title_font.render("請保持穩定！", True, DANGER_COLOR)
            warning_rect = warning_text.get_rect(center=(SCREEN_WIDTH // 2, 450))
            screen.blit(warning_text, warning_rect)

        # 曝光進度
        progress_label = f"曝光進度: {int(self.exposure_progress * 100)}%"
        progress_text = self.text_font.render(progress_label, True, WHITE)
        progress_rect = progress_text.get_rect(center=(SCREEN_WIDTH // 2, 555))
        screen.blit(progress_text, progress_rect)

        self.progress_bar.draw(screen)

        # 提示
        hint = "保持裝置穩定！"
        hint_surface = self.small_font.render(hint, True, LIGHT_GRAY)
        hint_rect = hint_surface.get_rect(center=(SCREEN_WIDTH // 2, 650))
        screen.blit(hint_surface, hint_rect)

    def _draw_result(self, screen: pygame.Surface):
        """繪製結果畫面"""
        # 標題
        title = self.title_font.render("曝光完成！", True, WHITE)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 50))
        screen.blit(title, title_rect)

        # 完成的晶圓
        self._draw_wafer_complete(screen, SCREEN_WIDTH // 2, 280)

        # 分數顯示
        score_color = SECONDARY_COLOR if self.exposure_score >= 70 else ACCENT_COLOR if self.exposure_score >= 40 else DANGER_COLOR
        score_text = f"曝光品質: {self.exposure_score} 分"
        score_surface = self.score_font.render(score_text, True, score_color)
        score_rect = score_surface.get_rect(center=(SCREEN_WIDTH // 2, 480))
        screen.blit(score_surface, score_rect)

        # 詳細說明
        if self.exposure_score >= 80:
            detail = "優秀！曝光均勻，圖案清晰"
        elif self.exposure_score >= 60:
            detail = "良好，但有些微晃動痕跡"
        else:
            detail = "曝光不均勻，需要改進穩定度"

        detail_surface = self.text_font.render(detail, True, LIGHT_GRAY)
        detail_rect = detail_surface.get_rect(center=(SCREEN_WIDTH // 2, 530))
        screen.blit(detail_surface, detail_rect)

        # 繼續按鈕
        self.next_button.draw(screen)

    def _draw_uv_light(self, screen: pygame.Surface):
        """繪製UV光效果"""
        center_x = SCREEN_WIDTH // 2
        center_y = 100

        # UV 光源
        pulse = 0.7 + 0.3 * math.sin(self.uv_pulse)
        base_radius = int(60 * pulse)

        # 光暈層
        for i in range(5, 0, -1):
            alpha = int(30 * pulse * (6 - i) / 5)
            radius = base_radius + i * 20
            surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            color = (*PHOTORESIST_PURPLE, alpha)
            pygame.draw.circle(surf, color, (radius, radius), radius)
            screen.blit(surf, (center_x - radius, center_y - radius))

        # 光束
        if self.current_stability >= self.STABILITY_THRESHOLD:
            beam_width = 200
            beam_alpha = int(80 * pulse)
        else:
            beam_width = 200 + int(50 * math.sin(self.uv_pulse * 5))
            beam_alpha = int(40 * pulse)

        beam_surf = pygame.Surface((beam_width, 200), pygame.SRCALPHA)
        pygame.draw.polygon(beam_surf, (*PHOTORESIST_PURPLE, beam_alpha), [
            (beam_width // 2, 0),
            (0, 200),
            (beam_width, 200)
        ])
        screen.blit(beam_surf, (center_x - beam_width // 2, center_y + 30))

    def _draw_wafer_preview(self, screen: pygame.Surface, cx: int, cy: int):
        """繪製晶圓預覽"""
        radius = 100

        # 晶圓底座
        pygame.draw.circle(screen, DARK_GRAY, (cx, cy), radius + 5)

        # 晶圓本體
        pygame.draw.circle(screen, SILICON_BLUE, (cx, cy), radius)

        # 光阻層（等待曝光）
        pygame.draw.circle(screen, PHOTORESIST_PURPLE, (cx, cy), radius - 10, 5)

        # 邊框
        pygame.draw.circle(screen, WHITE, (cx, cy), radius, 2)

    def _draw_wafer_exposing(self, screen: pygame.Surface, cx: int, cy: int):
        """繪製曝光中的晶圓"""
        radius = 100

        # 晶圓底座
        pygame.draw.circle(screen, DARK_GRAY, (cx, cy), radius + 5)

        # 晶圓本體
        pygame.draw.circle(screen, SILICON_BLUE, (cx, cy), radius)

        # 曝光進度效果（從中心向外擴展的光環）
        exposed_radius = int(radius * self.exposure_progress)
        if exposed_radius > 0:
            # 已曝光區域
            pulse = 0.8 + 0.2 * math.sin(self.uv_pulse)
            exposed_color = (
                int(PHOTORESIST_PURPLE[0] * pulse),
                int(PHOTORESIST_PURPLE[1] * pulse),
                int(PHOTORESIST_PURPLE[2] * pulse)
            )
            pygame.draw.circle(screen, exposed_color, (cx, cy), exposed_radius)

        # 未曝光光阻（外圈）
        pygame.draw.circle(screen, PHOTORESIST_PURPLE, (cx, cy), radius - 5, 3)

        # 穩定度視覺化 - 晃動時晶圓邊緣模糊
        if self.current_stability < self.STABILITY_THRESHOLD:
            shake = int(5 * (1 - self.current_stability))
            for i in range(3):
                offset_x = int(shake * math.sin(self.uv_pulse + i))
                offset_y = int(shake * math.cos(self.uv_pulse + i))
                blur_surf = pygame.Surface((radius * 2 + 20, radius * 2 + 20), pygame.SRCALPHA)
                pygame.draw.circle(blur_surf, (255, 0, 0, 30), (radius + 10, radius + 10), radius + 5, 2)
                screen.blit(blur_surf, (cx - radius - 10 + offset_x, cy - radius - 10 + offset_y))

        # 邊框
        pygame.draw.circle(screen, WHITE, (cx, cy), radius, 2)

    def _draw_wafer_complete(self, screen: pygame.Surface, cx: int, cy: int):
        """繪製完成的晶圓"""
        radius = 100

        # 晶圓底座
        pygame.draw.circle(screen, DARK_GRAY, (cx, cy), radius + 5)

        # 晶圓本體
        pygame.draw.circle(screen, SILICON_BLUE, (cx, cy), radius)

        # 曝光後的圖案（根據分數決定品質）
        quality = self.exposure_score / 100

        # 電路圖案網格
        grid_size = 15
        for i in range(-6, 7):
            for j in range(-6, 7):
                x = cx + i * grid_size
                y = cy + j * grid_size
                dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
                if dist < radius - 10:
                    # 根據品質決定圖案清晰度
                    if quality > 0.7:
                        pattern_color = SECONDARY_COLOR
                        size = 5
                    elif quality > 0.4:
                        pattern_color = ACCENT_COLOR
                        size = 4
                    else:
                        pattern_color = DANGER_COLOR
                        size = 3
                    pygame.draw.rect(screen, pattern_color, (x - size // 2, y - size // 2, size, size))

        # 邊框
        pygame.draw.circle(screen, WHITE, (cx, cy), radius, 3)

        # 品質標籤
        if quality > 0.7:
            label = "優質"
            label_color = SECONDARY_COLOR
        elif quality > 0.4:
            label = "合格"
            label_color = ACCENT_COLOR
        else:
            label = "不良"
            label_color = DANGER_COLOR

        label_surface = self.small_font.render(label, True, label_color)
        label_rect = label_surface.get_rect(center=(cx, cy + radius + 25))
        screen.blit(label_surface, label_rect)
