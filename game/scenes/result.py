"""
結果場景 - 顯示綜合評分與晶圓良率
"""

import pygame
import math
import random
from .base import Scene, Button
from ..config import *


class ResultScene(Scene):
    """結果場景"""

    # 分數對應的標籤
    SCORE_LABELS = {
        "purity": "材料純度",
        "uniformity": "薄膜均勻度",
        "exposure": "曝光品質",
        "precision": "蝕刻精準度",
    }

    # 各關卡評語 (5個級距)
    STAGE_COMMENTS = {
        "purity": {  # 第一關：材料純度
            90: "結晶完美無暇",
            80: "純度極佳",
            70: "雜質控制良好",
            60: "純度達標",
            0:  "需重新提煉",
        },
        "uniformity": {  # 第二關：薄膜均勻度
            90: "薄膜沉積完美",
            80: "膜厚均勻優異",
            70: "覆蓋率良好",
            60: "均勻度尚可",
            0:  "薄膜不均勻",
        },
        "exposure": {  # 第三關：曝光品質
            90: "曝光精準完美",
            80: "對焦極為銳利",
            70: "圖案清晰",
            60: "曝光品質達標",
            0:  "曝光失焦模糊",
        },
        "precision": {  # 第四關：蝕刻精準度
            90: "電路圖案完美",
            80: "線寬控制優異",
            70: "圖案還原良好",
            60: "圖案略有偏差",
            0:  "圖案偏差過大",
        },
    }

    # 總評評語 (5個級距)
    TOTAL_COMMENTS = {
        90: "良率頂尖！達到量產標準，可直接出貨！",
        80: "製程穩定，品質優異，已達業界水準！",
        70: "品質良好，微調參數後可提升良率。",
        60: "品質合格，建議檢視各製程環節。",
        0:  "良率偏低，需重新檢討製程參數。",
    }

    def __init__(self, game):
        super().__init__(game)

        # 計算結果
        self.total_score = 0
        self.grade = "D"
        self.yield_rate = 0

        # 動畫
        self.animation_progress = 0.0
        self.wafer_rotation = 0

        # UI 元件
        center_x = SCREEN_WIDTH // 2
        self.replay_button = Button(
            center_x - 320, 600, 190, 50,
            "再玩一次", PRIMARY_COLOR
        )
        self.leaderboard_button = Button(
            center_x - 95, 600, 190, 50,
            "排行榜", SECONDARY_COLOR
        )
        self.menu_button = Button(
            center_x + 130, 600, 190, 50,
            "主選單", GRAY
        )

        # 字體
        self.title_font = None
        self.large_font = None
        self.text_font = None
        self.small_font = None

    def on_enter(self):
        """進入場景"""
        self.title_font = pygame.font.SysFont("Microsoft JhengHei", 40)
        self.large_font = pygame.font.SysFont("Microsoft JhengHei", 48)
        self.text_font = pygame.font.SysFont("Microsoft JhengHei", 24)
        self.small_font = pygame.font.SysFont("Microsoft JhengHei", 18)

        # 預繪製漸層背景（效能優化）
        self._gradient_surface = self.create_gradient_background((60, 75, 100), factor=0.4)

        # 計算總分
        self._calculate_results()

        # 儲存成績到排行榜
        self._save_to_leaderboard()

        # 重設動畫
        self.animation_progress = 0.0

    def _calculate_results(self):
        """計算結果"""
        scores = self.game.scores

        # 加權總分（使用 config.py 中的 SCORE_WEIGHTS）
        self.total_score = 0
        for key, weight in SCORE_WEIGHTS.items():
            self.total_score += scores.get(key, 0) * (weight / 100)

        # 隨機加減 5 分（模擬製程變異）
        random_adjustment = random.randint(-5, 5)
        self.total_score = int(self.total_score) + random_adjustment

        # 限制在 0-100 範圍
        self.total_score = max(0, min(100, self.total_score))

        # 良率
        self.yield_rate = self.total_score

        # 等級 (5級制: S/A/B/C/D)
        if self.total_score >= 90:
            self.grade = "S"
        elif self.total_score >= 80:
            self.grade = "A"
        elif self.total_score >= 70:
            self.grade = "B"
        elif self.total_score >= 60:
            self.grade = "C"
        else:
            self.grade = "D"

    def _get_comment(self, score: int, comments_dict: dict) -> str:
        """根據分數取得對應評語"""
        if score >= 90:
            return comments_dict[90]
        elif score >= 80:
            return comments_dict[80]
        elif score >= 70:
            return comments_dict[70]
        elif score >= 60:
            return comments_dict[60]
        else:
            return comments_dict[0]

    def _save_to_leaderboard(self):
        """儲存成績到排行榜資料庫"""
        # 確保有玩家暱稱
        if not hasattr(self.game, 'player_nickname') or not self.game.player_nickname:
            return

        # 儲存到資料庫
        try:
            record_id = self.game.leaderboard_db.add_record(
                nickname=self.game.player_nickname,
                total_score=self.total_score,
                grade=self.grade,
                scores=self.game.scores
            )
            # 儲存紀錄 ID 供排行榜場景使用
            self.game._last_record_id = record_id
        except Exception:
            # 如果儲存失敗，靜默處理
            pass

    def handle_event(self, event: pygame.event.Event):
        """處理事件"""
        if self.replay_button.handle_event(event):
            # 重設分數
            for key in self.game.scores:
                self.game.scores[key] = 0
            self.switch_to("nickname")

        if self.leaderboard_button.handle_event(event):
            # 查看排行榜（不重設分數，讓排行榜場景處理）
            self.switch_to("leaderboard")

        if self.menu_button.handle_event(event):
            # 重設分數
            for key in self.game.scores:
                self.game.scores[key] = 0
            self.switch_to("menu")

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                for key in self.game.scores:
                    self.game.scores[key] = 0
                self.switch_to("menu")
            elif event.key == pygame.K_SPACE or event.key == pygame.K_RETURN:
                # 查看排行榜
                self.switch_to("leaderboard")

    def update(self, dt: float):
        """更新"""
        # 動畫進度
        if self.animation_progress < 1.0:
            self.animation_progress += dt * 0.5
            self.animation_progress = min(1.0, self.animation_progress)

        # 晶圓旋轉
        self.wafer_rotation += dt * 20

        # 更新按鈕動畫
        self.replay_button.update(dt)
        self.leaderboard_button.update(dt)
        self.menu_button.update(dt)

    def draw(self, screen: pygame.Surface):
        """繪製"""
        # 背景漸層
        for y in range(SCREEN_HEIGHT):
            ratio = y / SCREEN_HEIGHT
            r = int(20 + 15 * ratio)
            g = int(25 + 20 * ratio)
            b = int(40 + 30 * ratio)
            pygame.draw.line(screen, (r, g, b), (0, y), (SCREEN_WIDTH, y))

        # 標題
        self._draw_header(screen)

        # 成績單
        self._draw_scores(screen)

        # 總分和等級
        self._draw_total(screen)

        # 晶圓視覺化
        self._draw_wafer(screen)

        # 評語
        self._draw_comment(screen)

        # 按鈕
        self.replay_button.draw(screen)
        self.leaderboard_button.draw(screen)
        self.menu_button.draw(screen)

    def _draw_header(self, screen: pygame.Surface):
        """繪製標題"""
        # 主標題
        title = self.title_font.render("晶圓製作完成！", True, SECONDARY_COLOR)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 50))
        screen.blit(title, title_rect)

        # 副標題
        subtitle = self.text_font.render("品質評估報告", True, LIGHT_GRAY)
        subtitle_rect = subtitle.get_rect(center=(SCREEN_WIDTH // 2, 90))
        screen.blit(subtitle, subtitle_rect)

    def _draw_scores(self, screen: pygame.Surface):
        """繪製各項分數"""
        start_x = 100
        start_y = 150
        bar_width = 300
        bar_height = 25
        spacing = 60

        scores = self.game.scores

        for i, (key, label) in enumerate(self.SCORE_LABELS.items()):
            y = start_y + i * spacing
            score = scores.get(key, 0)
            weight = SCORE_WEIGHTS[key] / 100  # 轉換為小數

            # 動畫進度
            animated_score = score * min(self.animation_progress * 2, 1.0)

            # 標籤
            label_text = self.text_font.render(label, True, WHITE)
            screen.blit(label_text, (start_x, y))

            # 權重
            weight_text = self.small_font.render(f"({int(weight * 100)}%)", True, GRAY)
            screen.blit(weight_text, (start_x + 200, y + 5))

            # 進度條背景
            bar_y = y + 28
            pygame.draw.rect(screen, DARK_GRAY, (start_x, bar_y, bar_width, bar_height), border_radius=5)

            # 進度條填充
            fill_width = int(bar_width * animated_score / 100)
            if fill_width > 0:
                if score >= 80:
                    color = SECONDARY_COLOR
                elif score >= 60:
                    color = PRIMARY_COLOR
                else:
                    color = ACCENT_COLOR
                pygame.draw.rect(screen, color, (start_x, bar_y, fill_width, bar_height), border_radius=5)

            # 分數文字
            score_text = self.text_font.render(f"{int(animated_score)}/100", True, WHITE)
            score_rect = score_text.get_rect(midleft=(start_x + bar_width + 20, bar_y + bar_height // 2))
            screen.blit(score_text, score_rect)

            # 評語（動畫完成後才顯示）
            if self.animation_progress >= 0.8:
                comment = self._get_comment(score, self.STAGE_COMMENTS[key])
                # 根據分數決定顏色
                if score >= 80:
                    comment_color = SECONDARY_COLOR
                elif score >= 60:
                    comment_color = PRIMARY_COLOR
                else:
                    comment_color = ACCENT_COLOR

                comment_text = self.small_font.render(comment, True, comment_color)
                comment_rect = comment_text.get_rect(midleft=(start_x + bar_width + 100, bar_y + bar_height // 2))
                screen.blit(comment_text, comment_rect)

    def _draw_total(self, screen: pygame.Surface):
        """繪製總分"""
        center_x = SCREEN_WIDTH // 2
        y = 420

        # 動畫進度
        animated_total = self.total_score * self.animation_progress

        # 總分標籤
        label = self.text_font.render("良率：", True, WHITE)
        label_rect = label.get_rect(center=(center_x - 100, y))
        screen.blit(label, label_rect)

        # 總分數字
        score_text = self.large_font.render(f"{int(animated_total)}%", True, WHITE)
        score_rect = score_text.get_rect(center=(center_x + 50, y))
        screen.blit(score_text, score_rect)

        # 等級 (5級制)
        grade_colors = {
            "S": SECONDARY_COLOR,  # 綠色（頂尖）
            "A": SECONDARY_COLOR,  # 綠色
            "B": PRIMARY_COLOR,    # 藍色
            "C": ACCENT_COLOR,     # 黃色
            "D": DANGER_COLOR,     # 紅色
        }
        grade_color = grade_colors.get(self.grade, WHITE)

        # 等級框
        grade_x = center_x + 150
        pygame.draw.rect(screen, grade_color, (grade_x - 30, y - 35, 60, 70), border_radius=10)

        grade_text = self.large_font.render(self.grade, True, WHITE)
        grade_rect = grade_text.get_rect(center=(grade_x, y))
        screen.blit(grade_text, grade_rect)

    def _draw_wafer(self, screen: pygame.Surface):
        """繪製晶圓"""
        wafer_x = SCREEN_WIDTH - 200
        wafer_y = 280
        radius = 100

        # 晶圓底座
        pygame.draw.circle(screen, (40, 50, 70), (wafer_x, wafer_y), radius + 10)

        # 晶圓本體
        pygame.draw.circle(screen, SILICON_BLUE, (wafer_x, wafer_y), radius)

        # 根據分數繪製品質
        quality = self.total_score / 100

        # 電路圖案
        pattern_alpha = int(255 * quality * self.animation_progress)
        for i in range(-4, 5):
            for j in range(-4, 5):
                if i * i + j * j <= 16:
                    # 根據良率決定晶片顏色
                    if quality > 0.75:
                        chip_color = SECONDARY_COLOR
                    elif quality > 0.5:
                        chip_color = PRIMARY_COLOR
                    else:
                        chip_color = ACCENT_COLOR

                    x = wafer_x + i * 18
                    y = wafer_y + j * 18
                    pygame.draw.rect(screen, chip_color, (x - 7, y - 7, 14, 14))

        # 旋轉光澤效果
        shine_angle = self.wafer_rotation * math.pi / 180
        shine_x = wafer_x + int(math.cos(shine_angle) * radius * 0.7)
        shine_y = wafer_y + int(math.sin(shine_angle) * radius * 0.7)
        pygame.draw.circle(screen, (255, 255, 255, 100), (shine_x, shine_y), 15)

        # 標籤
        label = self.small_font.render("最終晶圓", True, LIGHT_GRAY)
        label_rect = label.get_rect(center=(wafer_x, wafer_y + radius + 30))
        screen.blit(label, label_rect)

    def _draw_comment(self, screen: pygame.Surface):
        """繪製總評語"""
        center_x = SCREEN_WIDTH // 2
        y = 500

        # 使用 5 級評語系統
        comment = self._get_comment(self.total_score, self.TOTAL_COMMENTS)

        # 顏色對應
        if self.total_score >= 90:
            color = SECONDARY_COLOR  # 綠色
        elif self.total_score >= 80:
            color = SECONDARY_COLOR
        elif self.total_score >= 70:
            color = PRIMARY_COLOR    # 藍色
        elif self.total_score >= 60:
            color = ACCENT_COLOR     # 黃色
        else:
            color = DANGER_COLOR     # 紅色

        # 只有動畫完成後才顯示
        if self.animation_progress >= 0.8:
            comment_text = self.text_font.render(comment, True, color)
            comment_rect = comment_text.get_rect(center=(center_x, y))
            screen.blit(comment_text, comment_rect)

            # 提示
            hint = self.small_font.render("按 SPACE 查看排行榜，ESC 返回選單", True, GRAY)
            hint_rect = hint.get_rect(center=(center_x, y + 40))
            screen.blit(hint, hint_rect)
