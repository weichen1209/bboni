"""
第四關：手繪電路
玩家使用 webcam 和手部追蹤，在螢幕上繪製 H 形電路圖案
使用相似度模型評分
"""

import pygame
import cv2
import numpy as np
from typing import List, Tuple, Optional
from .base import Scene, Button, ProgressBar
from ..config import *
from ..utils.hand_tracker import HandTracker
from ..utils.cv_scoring import ShapeSimilarityScorer, ShapeType, SHAPE_METADATA


class EtchingStage(Scene):
    """手繪電路關卡 - 使用 webcam 手部追蹤"""

    # 遊戲階段
    PHASE_LOADING = 0       # 載入攝影機
    PHASE_INSTRUCTIONS = 1  # 操作說明
    PHASE_DRAWING = 2       # 繪圖中
    PHASE_RESULT = 3        # 顯示結果

    # 繪圖參數
    DRAWING_DURATION = 20.0       # 繪圖時間限制 (秒)
    WEBCAM_WIDTH = 640
    WEBCAM_HEIGHT = 480
    TRAIL_COLOR = (0, 255, 255)   # 軌跡顏色 (BGR - 青色)
    TRAIL_THICKNESS = 6           # 軌跡粗細

    def __init__(self, game):
        super().__init__(game)

        # 遊戲階段
        self.phase = self.PHASE_LOADING

        # 手部追蹤器
        self.hand_tracker: Optional[HandTracker] = None

        # 繪圖狀態
        self.drawing_points: List[Tuple[int, int]] = []
        self.drawing_elapsed = 0.0

        # 評分器
        self.scorer: Optional[ShapeSimilarityScorer] = None

        # 分數
        self.precision_score = 0
        self.coverage_score = 0
        self.iou_score = 0

        # Webcam 顯示位置（置中）
        self.webcam_x = (SCREEN_WIDTH - self.WEBCAM_WIDTH) // 2
        self.webcam_y = 60

        # 目標圖形疊加層
        self._target_overlay: Optional[pygame.Surface] = None

        # 載入狀態
        self._loading_progress = 0.0
        self._loading_message = "初始化..."

        # UI 元件
        center_x = SCREEN_WIDTH // 2
        self.start_button = Button(
            center_x - 100, 650, 200, 50,
            "開始繪圖", PRIMARY_COLOR
        )
        self.finish_button = Button(
            center_x - 100, 650, 200, 50,
            "完成", SECONDARY_COLOR
        )
        self.next_button = Button(
            center_x - 100, 650, 200, 50,
            "查看結果", PRIMARY_COLOR
        )
        self.timer_bar = ProgressBar(
            center_x - 250, 590, 500, 16,
            bg_color=DARK_GRAY,
            fill_color=ACCENT_COLOR,
            border_color=GRAY
        )

        # 字體
        self.title_font = None
        self.text_font = None
        self.small_font = None
        self.score_font = None

    def on_enter(self):
        """進入場景"""
        super().on_enter()
        self.title_font = pygame.font.SysFont("Microsoft JhengHei", 42)
        self.text_font = pygame.font.SysFont("Microsoft JhengHei", 24)
        self.small_font = pygame.font.SysFont("Microsoft JhengHei", 18)
        self.score_font = pygame.font.SysFont("Microsoft JhengHei", 48)

        # 預繪製增強版漸層背景
        self._bg_surface = self.create_enhanced_background(PLASMA_CYAN_DARK, add_vignette=True, add_grid=True)

        # 重置狀態 - 直接從載入階段開始（圖形已在第三關選擇）
        self.phase = self.PHASE_LOADING
        self.drawing_points = []
        self.drawing_elapsed = 0.0
        self.precision_score = 0
        self._loading_progress = 0.0
        self._loading_message = "初始化攝影機..."

        # 初始化評分器（使用第三關選擇的圖形）
        self.scorer = ShapeSimilarityScorer((self.WEBCAM_WIDTH, self.WEBCAM_HEIGHT))
        self.scorer.create_target_image(self.game.selected_shape_type, thickness=12)

        # 建立目標圖形疊加層
        self._create_target_overlay()

        # 開始初始化手部追蹤器
        self._init_hand_tracker()

    def _init_hand_tracker(self):
        """初始化手部追蹤器"""
        self.hand_tracker = HandTracker(
            camera_index=0,
            width=self.WEBCAM_WIDTH,
            height=self.WEBCAM_HEIGHT
        )

        if self.hand_tracker.start():
            self._loading_message = "載入完成！"
            self._loading_progress = 1.0
            self.phase = self.PHASE_INSTRUCTIONS
        else:
            self._loading_message = "無法開啟攝影機！"
            self._loading_progress = 0.0

    def _create_target_overlay(self):
        """建立目標圖形的 pygame 疊加層"""
        if self.scorer is None:
            return

        # 取得 BGRA 格式的疊加圖像
        overlay_bgra = self.scorer.get_target_overlay_image(alpha=0.4, color=(0, 255, 100))

        # 轉換為 pygame surface
        # OpenCV 是 BGRA，pygame 需要 RGBA
        overlay_rgba = cv2.cvtColor(overlay_bgra, cv2.COLOR_BGRA2RGBA)

        self._target_overlay = pygame.image.frombuffer(
            overlay_rgba.tobytes(),
            (self.WEBCAM_WIDTH, self.WEBCAM_HEIGHT),
            'RGBA'
        )

    def on_exit(self):
        """離開場景"""
        super().on_exit()
        if self.hand_tracker:
            self.hand_tracker.stop()
            self.hand_tracker = None

    def handle_event(self, event: pygame.event.Event):
        """處理事件"""
        if self.phase == self.PHASE_INSTRUCTIONS:
            self._handle_instructions_event(event)
        elif self.phase == self.PHASE_DRAWING:
            self._handle_drawing_event(event)
        elif self.phase == self.PHASE_RESULT:
            self._handle_result_event(event)

        # ESC 返回選單
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.switch_to("menu")

    def _handle_instructions_event(self, event: pygame.event.Event):
        """指示階段事件處理"""
        if self.start_button.handle_event(event):
            self._start_drawing()

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE or event.key == pygame.K_RETURN:
                self._start_drawing()

    def _handle_drawing_event(self, event: pygame.event.Event):
        """繪圖階段事件處理"""
        if self.finish_button.handle_event(event):
            self._finish_drawing()

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE or event.key == pygame.K_RETURN:
                self._finish_drawing()

    def _handle_result_event(self, event: pygame.event.Event):
        """結果階段事件處理"""
        if self.next_button.handle_event(event):
            self._finish_stage()

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE or event.key == pygame.K_RETURN:
                self._finish_stage()

    def _start_drawing(self):
        """開始繪圖階段"""
        self.phase = self.PHASE_DRAWING
        self.drawing_points = []
        self.drawing_elapsed = 0.0

    def _finish_drawing(self):
        """完成繪圖，計算分數"""
        if self.scorer and len(self.drawing_points) > 10:
            total_score, scores = self.scorer.get_combined_score(self.drawing_points)
            self.precision_score = total_score
            self.coverage_score = int(scores.get("coverage", 0))
            self.iou_score = int(scores.get("iou", 0))
        else:
            self.precision_score = 0
            self.coverage_score = 0
            self.iou_score = 0

        self.game.scores["precision"] = self.precision_score
        self.phase = self.PHASE_RESULT

    def _finish_stage(self):
        """完成關卡，進入結果畫面"""
        self.switch_to("result")

    def update(self, dt: float):
        """更新遊戲邏輯"""
        # 更新淡入淡出
        self.update_fade(dt)

        # 更新按鈕動畫
        self.start_button.update(dt)
        self.finish_button.update(dt)
        self.next_button.update(dt)
        self.timer_bar.update(dt)

        if self.phase == self.PHASE_LOADING:
            pass  # 等待載入完成
        elif self.phase == self.PHASE_INSTRUCTIONS:
            self._update_webcam()
        elif self.phase == self.PHASE_DRAWING:
            self._update_drawing_phase(dt)
        elif self.phase == self.PHASE_RESULT:
            pass

    def _update_webcam(self):
        """更新 webcam（不記錄軌跡）"""
        if self.hand_tracker and self.hand_tracker.is_running:
            self.hand_tracker.update()

    def _update_drawing_phase(self, dt: float):
        """繪圖階段更新"""
        # 更新計時
        self.drawing_elapsed += dt
        remaining = max(0, self.DRAWING_DURATION - self.drawing_elapsed)
        self.timer_bar.set_progress(remaining / self.DRAWING_DURATION)

        # 更新 webcam 和手部追蹤
        if self.hand_tracker and self.hand_tracker.is_running:
            if self.hand_tracker.update():
                # 取得食指位置
                finger_pos = self.hand_tracker.get_index_finger_tip()
                if finger_pos:
                    self.drawing_points.append(finger_pos)

        # 檢查時間結束
        if self.drawing_elapsed >= self.DRAWING_DURATION:
            self._finish_drawing()

    def draw(self, screen: pygame.Surface):
        """繪製場景"""
        self._draw_background(screen)

        if self.phase == self.PHASE_LOADING:
            self._draw_loading(screen)
        elif self.phase == self.PHASE_INSTRUCTIONS:
            self._draw_instructions(screen)
        elif self.phase == self.PHASE_DRAWING:
            self._draw_drawing_phase(screen)
        elif self.phase == self.PHASE_RESULT:
            self._draw_result(screen)

        # 淡入淡出遮罩
        self.draw_fade_overlay(screen)

    def _draw_background(self, screen: pygame.Surface):
        """繪製漸層背景"""
        screen.blit(self._bg_surface, (0, 0))

    def _draw_loading(self, screen: pygame.Surface):
        """繪製載入畫面"""
        # 標題
        title = self.title_font.render("蝕刻 - 精準控制", True, WHITE)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50))
        screen.blit(title, title_rect)

        # 載入訊息
        msg = self.text_font.render(self._loading_message, True, TEXT_SECONDARY)
        msg_rect = msg.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 20))
        screen.blit(msg, msg_rect)

    def _draw_instructions(self, screen: pygame.Surface):
        """繪製指示畫面"""
        # 標題
        self.draw_title(screen, "蝕刻 - 精準控制", y=30, font=self.title_font)

        # Webcam 畫面 + 目標疊加
        self._draw_webcam_with_overlay(screen, show_trail=False)

        # 說明文字（顯示選中的圖形名稱）
        shape_name = SHAPE_METADATA[self.game.selected_shape_type]["name"]
        instructions = [
            f"用食指對著鏡頭描繪 {shape_name} 圖案",
            "綠色輪廓是目標圖形",
        ]

        y_start = self.webcam_y + self.WEBCAM_HEIGHT + 15
        for i, text in enumerate(instructions):
            surface = self.text_font.render(text, True, TEXT_SECONDARY)
            rect = surface.get_rect(center=(SCREEN_WIDTH // 2, y_start + i * 28))
            screen.blit(surface, rect)

        # 開始按鈕
        self.start_button.draw(screen)

    def _draw_drawing_phase(self, screen: pygame.Surface):
        """繪製繪圖階段"""
        # 標題（包含手部偵測提示）
        if self.hand_tracker and not self.hand_tracker.has_hand():
            title_text = "請將手放入畫面"
            title_color = DANGER_COLOR
        else:
            title_text = "描繪中！"
            title_color = WHITE

        title = self.title_font.render(title_text, True, title_color)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 30))
        screen.blit(title, title_rect)

        # Webcam 畫面 + 目標 + 軌跡
        self._draw_webcam_with_overlay(screen, show_trail=True)

        # 計時器
        remaining = max(0, self.DRAWING_DURATION - self.drawing_elapsed)
        timer_text = f"剩餘時間: {remaining:.1f}s"
        timer_surface = self.text_font.render(timer_text, True, WHITE)
        timer_rect = timer_surface.get_rect(center=(SCREEN_WIDTH // 2, self.webcam_y + self.WEBCAM_HEIGHT + 15))
        screen.blit(timer_surface, timer_rect)

        # 進度條 (使用初始化位置)
        self.timer_bar.draw(screen)

        # 完成按鈕 (使用初始化位置)
        self.finish_button.draw(screen)

    def _draw_result(self, screen: pygame.Surface):
        """繪製結果畫面"""
        # 標題
        title = self.title_font.render("繪圖完成！", True, WHITE)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 30))
        screen.blit(title, title_rect)

        # 顯示最終繪製結果（靜態）
        self._draw_final_result(screen)

        # 分數顯示
        score_color = SECONDARY_COLOR if self.precision_score >= 70 else ACCENT_COLOR if self.precision_score >= 40 else DANGER_COLOR
        score_text = f"相似度: {self.precision_score} 分"
        score_surface = self.score_font.render(score_text, True, score_color)
        score_rect = score_surface.get_rect(center=(SCREEN_WIDTH // 2, self.webcam_y + self.WEBCAM_HEIGHT + 20))
        screen.blit(score_surface, score_rect)

        # 詳細分數
        details = [
            f"覆蓋率: {self.coverage_score}%",
            f"IoU: {self.iou_score}%",
        ]

        y_start = self.webcam_y + self.WEBCAM_HEIGHT + 60
        for i, text in enumerate(details):
            surface = self.small_font.render(text, True, LIGHT_GRAY)
            rect = surface.get_rect(center=(SCREEN_WIDTH // 2, y_start + i * 22))
            screen.blit(surface, rect)

        # 繼續按鈕 (使用初始化位置)
        self.next_button.draw(screen)

    def _draw_webcam_with_overlay(self, screen: pygame.Surface, show_trail: bool):
        """繪製 webcam 畫面並疊加目標和軌跡"""
        if self.hand_tracker is None or not self.hand_tracker.is_running:
            # 顯示佔位符
            pygame.draw.rect(screen, DARK_GRAY,
                           (self.webcam_x, self.webcam_y, self.WEBCAM_WIDTH, self.WEBCAM_HEIGHT))
            no_cam = self.text_font.render("攝影機未啟動", True, TEXT_MUTED)
            no_cam_rect = no_cam.get_rect(center=(self.webcam_x + self.WEBCAM_WIDTH // 2,
                                                   self.webcam_y + self.WEBCAM_HEIGHT // 2))
            screen.blit(no_cam, no_cam_rect)
            return

        # 取得 webcam 畫面
        frame = self.hand_tracker.get_frame()
        if frame is None:
            return

        # 繪製手部骨架
        frame = self.hand_tracker.draw_hand_landmarks(frame)

        # 繪製軌跡
        if show_trail and len(self.drawing_points) > 1:
            pts = np.array(self.drawing_points, dtype=np.int32)
            cv2.polylines(frame, [pts], isClosed=False,
                         color=self.TRAIL_COLOR, thickness=self.TRAIL_THICKNESS)

            # 繪製當前點
            if self.drawing_points:
                last_point = self.drawing_points[-1]
                cv2.circle(frame, last_point, 10, (0, 255, 255), -1)

        # 轉換 BGR 到 RGB 並建立 pygame surface
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_surface = pygame.image.frombuffer(
            frame_rgb.tobytes(),
            (self.WEBCAM_WIDTH, self.WEBCAM_HEIGHT),
            'RGB'
        )

        # 繪製 webcam 畫面
        screen.blit(frame_surface, (self.webcam_x, self.webcam_y))

        # 疊加目標圖形
        if self._target_overlay:
            screen.blit(self._target_overlay, (self.webcam_x, self.webcam_y))

        # 邊框
        pygame.draw.rect(screen, WHITE,
                        (self.webcam_x - 2, self.webcam_y - 2,
                         self.WEBCAM_WIDTH + 4, self.WEBCAM_HEIGHT + 4), 2)

    def _draw_final_result(self, screen: pygame.Surface):
        """繪製最終結果比較圖"""
        if self.scorer is None:
            return

        # 建立結果圖像
        result_img = np.zeros((self.WEBCAM_HEIGHT, self.WEBCAM_WIDTH, 3), dtype=np.uint8)
        result_img[:] = (40, 40, 40)  # 深灰背景

        # 繪製目標圖形（綠色）
        target_img = self.scorer._target_image
        if target_img is not None:
            target_mask = target_img > 0
            result_img[target_mask] = (0, 150, 0)  # 深綠色

        # 繪製用戶軌跡（青色）
        if len(self.drawing_points) > 1:
            pts = np.array(self.drawing_points, dtype=np.int32)
            cv2.polylines(result_img, [pts], isClosed=False,
                         color=(255, 255, 0), thickness=self.TRAIL_THICKNESS)

        # 轉換為 pygame surface
        result_rgb = cv2.cvtColor(result_img, cv2.COLOR_BGR2RGB)
        result_surface = pygame.image.frombuffer(
            result_rgb.tobytes(),
            (self.WEBCAM_WIDTH, self.WEBCAM_HEIGHT),
            'RGB'
        )

        screen.blit(result_surface, (self.webcam_x, self.webcam_y))

        # 邊框
        pygame.draw.rect(screen, WHITE,
                        (self.webcam_x - 2, self.webcam_y - 2,
                         self.WEBCAM_WIDTH + 4, self.WEBCAM_HEIGHT + 4), 2)

        # 圖例
        legend_y = self.webcam_y - 25
        pygame.draw.rect(screen, (0, 150, 0), (self.webcam_x, legend_y, 15, 15))
        legend1 = self.small_font.render("目標", True, TEXT_SECONDARY)
        screen.blit(legend1, (self.webcam_x + 20, legend_y - 2))

        pygame.draw.rect(screen, (0, 255, 255), (self.webcam_x + 80, legend_y, 15, 15))
        legend2 = self.small_font.render("你的繪製", True, TEXT_SECONDARY)
        screen.blit(legend2, (self.webcam_x + 100, legend_y - 2))
