"""
排行榜場景
"""

import pygame
from .base import Scene, Button
from ..config import *
from ..database import LeaderboardDB


# 獎牌顏色
GOLD_COLOR = (255, 215, 0)
SILVER_COLOR = (192, 192, 192)
BRONZE_COLOR = (205, 127, 50)


class LeaderboardScene(Scene):
    """排行榜場景"""

    def __init__(self, game):
        super().__init__(game)

        center_x = SCREEN_WIDTH // 2

        # 資料庫
        self.db = LeaderboardDB()
        self.records = []
        self.current_record_id = None
        self.current_player_rank = None

        # 來源標記（是否從結算畫面進入）
        self.from_result = False

        # 按鈕
        self.menu_button = Button(
            center_x - 220, 600, 200, 50,
            "返回主選單", GRAY
        )
        self.replay_button = Button(
            center_x + 20, 600, 200, 50,
            "再玩一次", PRIMARY_COLOR
        )

        # 字體
        self.title_font = None
        self.header_font = None
        self.text_font = None
        self.rank_font = None

    def on_enter(self):
        """進入場景"""
        # 初始化字體
        self.title_font = pygame.font.SysFont("Microsoft JhengHei", 42)
        self.header_font = pygame.font.SysFont("Microsoft JhengHei", 20)
        self.text_font = pygame.font.SysFont("Microsoft JhengHei", 24)
        self.rank_font = pygame.font.SysFont("Microsoft JhengHei", 28)

        # 預繪製漸層背景
        self._gradient_surface = self.create_gradient_background((50, 70, 100), factor=0.4)

        # 載入排行榜資料
        self.records = self.db.get_top_records(10)

        # 檢查是否有新紀錄需要高亮
        if hasattr(self.game, '_last_record_id') and self.game._last_record_id:
            self.current_record_id = self.game._last_record_id
            self.current_player_rank = self.db.get_player_rank(self.current_record_id)
            self.from_result = True
            # 清除標記
            del self.game._last_record_id
        else:
            self.current_record_id = None
            self.current_player_rank = None
            self.from_result = False

    def handle_event(self, event: pygame.event.Event):
        """處理事件"""
        if self.menu_button.handle_event(event):
            self._reset_scores()
            self.switch_to("menu")

        if self.replay_button.handle_event(event):
            self._reset_scores()
            self.switch_to("nickname")

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._reset_scores()
                self.switch_to("menu")
            elif event.key == pygame.K_SPACE or event.key == pygame.K_RETURN:
                self._reset_scores()
                self.switch_to("nickname")

    def _reset_scores(self):
        """重設分數"""
        for key in self.game.scores:
            self.game.scores[key] = 0

    def update(self, dt: float):
        """更新"""
        self.menu_button.update(dt)
        self.replay_button.update(dt)

    def draw(self, screen: pygame.Surface):
        """繪製"""
        # 背景
        screen.blit(self._gradient_surface, (0, 0))

        center_x = SCREEN_WIDTH // 2

        # 標題
        title_text = self.title_font.render("排行榜", True, ACCENT_COLOR)
        title_rect = title_text.get_rect(center=(center_x, 50))
        screen.blit(title_text, title_rect)

        # 繪製表格
        self._draw_table(screen)

        # 按鈕
        self.menu_button.draw(screen)
        self.replay_button.draw(screen)

        # 提示
        hint_font = pygame.font.SysFont("Microsoft JhengHei", 16)
        hint_text = hint_font.render(
            "按 SPACE 再玩一次，ESC 返回主選單", True, GRAY
        )
        hint_rect = hint_text.get_rect(center=(center_x, 570))
        screen.blit(hint_text, hint_rect)

    def _draw_table(self, screen: pygame.Surface):
        """繪製排行榜表格"""
        center_x = SCREEN_WIDTH // 2
        table_width = 600
        table_x = center_x - table_width // 2
        header_y = 110
        row_height = 45
        start_y = header_y + 40

        # 表頭背景
        header_bg = pygame.Surface((table_width, 35), pygame.SRCALPHA)
        header_bg.fill((40, 50, 70, 200))
        screen.blit(header_bg, (table_x, header_y))

        # 表頭文字
        headers = [
            ("排名", table_x + 50),
            ("暱稱", table_x + 180),
            ("分數", table_x + 380),
            ("等級", table_x + 500)
        ]
        for text, x in headers:
            header_surface = self.header_font.render(text, True, TEXT_SECONDARY)
            header_rect = header_surface.get_rect(center=(x, header_y + 17))
            screen.blit(header_surface, header_rect)

        # 無資料提示
        if not self.records:
            empty_text = self.text_font.render("尚無紀錄", True, TEXT_MUTED)
            empty_rect = empty_text.get_rect(center=(center_x, start_y + 100))
            screen.blit(empty_text, empty_rect)
            return

        # 繪製每一行
        for i, record in enumerate(self.records):
            y = start_y + i * row_height
            rank = i + 1

            # 檢查是否為當前玩家
            is_current = (self.current_record_id is not None and
                         record.id == self.current_record_id)

            # 行背景
            row_bg = pygame.Surface((table_width, row_height - 5), pygame.SRCALPHA)
            if is_current:
                # 當前玩家高亮
                row_bg.fill((52, 152, 219, 80))
            elif i % 2 == 0:
                row_bg.fill((35, 45, 65, 150))
            else:
                row_bg.fill((25, 35, 55, 150))
            screen.blit(row_bg, (table_x, y))

            # 當前玩家邊框
            if is_current:
                pygame.draw.rect(screen, PRIMARY_COLOR,
                               (table_x, y, table_width, row_height - 5),
                               width=2, border_radius=5)

            # 排名
            self._draw_rank(screen, rank, table_x + 50, y + row_height // 2 - 2)

            # 暱稱
            name_color = WHITE if is_current else TEXT_PRIMARY
            name_text = self.text_font.render(record.nickname, True, name_color)
            name_rect = name_text.get_rect(center=(table_x + 180, y + row_height // 2 - 2))
            screen.blit(name_text, name_rect)

            # 分數
            score_color = SECONDARY_COLOR if record.total_score >= 90 else (
                PRIMARY_COLOR if record.total_score >= 75 else (
                    ACCENT_COLOR if record.total_score >= 60 else DANGER_COLOR
                )
            )
            score_text = self.text_font.render(f"{record.total_score}%", True, score_color)
            score_rect = score_text.get_rect(center=(table_x + 380, y + row_height // 2 - 2))
            screen.blit(score_text, score_rect)

            # 等級
            grade_colors = {
                "A": SECONDARY_COLOR,
                "B": PRIMARY_COLOR,
                "C": ACCENT_COLOR,
                "D": DANGER_COLOR,
            }
            grade_color = grade_colors.get(record.grade, WHITE)
            grade_text = self.rank_font.render(record.grade, True, grade_color)
            grade_rect = grade_text.get_rect(center=(table_x + 500, y + row_height // 2 - 2))
            screen.blit(grade_text, grade_rect)

        # 如果當前玩家不在前10名，顯示其排名
        if self.current_player_rank and self.current_player_rank > 10:
            self._draw_current_player_rank(screen, table_x, start_y + 10 * row_height)

    def _draw_rank(self, screen: pygame.Surface, rank: int, x: int, y: int):
        """繪製排名（前三名特殊樣式）"""
        if rank == 1:
            # 金牌
            pygame.draw.circle(screen, GOLD_COLOR, (x, y), 15)
            rank_text = self.rank_font.render("1", True, (50, 40, 0))
        elif rank == 2:
            # 銀牌
            pygame.draw.circle(screen, SILVER_COLOR, (x, y), 15)
            rank_text = self.rank_font.render("2", True, (40, 40, 40))
        elif rank == 3:
            # 銅牌
            pygame.draw.circle(screen, BRONZE_COLOR, (x, y), 15)
            rank_text = self.rank_font.render("3", True, (60, 30, 10))
        else:
            # 一般排名
            rank_text = self.text_font.render(str(rank), True, TEXT_PRIMARY)

        rank_rect = rank_text.get_rect(center=(x, y))
        screen.blit(rank_text, rank_rect)

    def _draw_current_player_rank(self, screen: pygame.Surface, table_x: int, y: int):
        """繪製當前玩家排名（如果不在前10名）"""
        record = self.db.get_record_by_id(self.current_record_id)
        if not record:
            return

        # 分隔線
        pygame.draw.line(screen, GRAY,
                        (table_x, y + 10),
                        (table_x + 600, y + 10), 1)

        # 您的排名文字
        your_rank_text = self.text_font.render(
            f"您的排名: 第 {self.current_player_rank} 名",
            True, PRIMARY_COLOR
        )
        your_rank_rect = your_rank_text.get_rect(center=(SCREEN_WIDTH // 2, y + 35))
        screen.blit(your_rank_text, your_rank_rect)
