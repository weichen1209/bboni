"""
科普知識介紹場景
在每一關遊戲開始前，顯示該關卡對應的半導體製程知識
"""

import pygame
from .base import Scene, Button
from ..config import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    WHITE, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    PRIMARY_COLOR, PRIMARY_LIGHT,
    SAND_YELLOW, SILICON_BLUE, UV_PURPLE, PLASMA_CYAN
)


# 各關卡的科普知識內容
INTRO_CONTENT = {
    1: {
        "title": "第一關：材料準備",
        "content": "沙子含有矽，經過高溫提煉成多晶矽，再拉製成整齊排列的單晶矽，切片後就是製作晶片的「晶圓」。",
        "next_scene": "stage1",
        "theme_color": SAND_YELLOW,
    },
    2: {
        "title": "第二關：薄膜沉積",
        "content": "在晶圓表面鍍上一層極薄的材料，厚度比頭髮細上萬倍。塗覆越均勻，晶片品質越好。",
        "next_scene": "stage2",
        "theme_color": SILICON_BLUE,
    },
    3: {
        "title": "第三關：光刻曝光",
        "content": "用光線將電路圖案投影到晶圓上，過程中必須保持穩定，任何晃動都會讓圖案模糊失敗。",
        "next_scene": "stage3",
        "theme_color": UV_PURPLE,
    },
    4: {
        "title": "第四關：蝕刻",
        "content": "用化學或電漿方式移除多餘材料，刻出精確的電路圖案。方向和力道的控制是成功關鍵。",
        "next_scene": "stage4",
        "theme_color": PLASMA_CYAN,
    },
}


class IntroScene(Scene):
    """科普知識介紹場景基底類別"""

    STAGE_NUMBER = 1  # 子類別覆寫此值

    def __init__(self, game):
        super().__init__(game)

        config = INTRO_CONTENT[self.STAGE_NUMBER]
        self.title = config["title"]
        self.content = config["content"]
        self.next_scene = config["next_scene"]
        self.theme_color = config["theme_color"]

        # UI 元件
        center_x = SCREEN_WIDTH // 2
        self.continue_button = Button(
            center_x - 100, 520, 200, 50,
            "開始遊戲", PRIMARY_COLOR, PRIMARY_LIGHT
        )

        # 字體（在 on_enter 初始化）
        self.title_font = None
        self.text_font = None
        self.small_font = None
        self.stage_font = None

        # 背景
        self._bg_surface = None

    def on_enter(self):
        """進入場景"""
        super().on_enter()

        # 初始化字體
        self.title_font = pygame.font.SysFont("Microsoft JhengHei", 48)
        self.text_font = pygame.font.SysFont("Microsoft JhengHei", 28)
        self.small_font = pygame.font.SysFont("Microsoft JhengHei", 20)
        self.stage_font = pygame.font.SysFont("Microsoft JhengHei", 24)

        # 預繪製背景
        self._bg_surface = self.create_enhanced_background(
            self.theme_color, add_vignette=True, add_grid=False
        )

    def handle_event(self, event: pygame.event.Event):
        """處理事件"""
        # 按鈕點擊
        if self.continue_button.handle_event(event):
            self.switch_to(self.next_scene)

        # 鍵盤快捷鍵
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                self.switch_to(self.next_scene)
            elif event.key == pygame.K_ESCAPE:
                self.switch_to("menu")

    def update(self, dt: float):
        """更新"""
        self.update_fade(dt)
        self.continue_button.update(dt)

    def draw(self, screen: pygame.Surface):
        """繪製場景"""
        # 背景
        screen.blit(self._bg_surface, (0, 0))

        center_x = SCREEN_WIDTH // 2

        # 關卡編號
        stage_text = f"Stage {self.STAGE_NUMBER}"
        stage_surface = self.stage_font.render(stage_text, True, TEXT_MUTED)
        stage_rect = stage_surface.get_rect(center=(center_x, 120))
        screen.blit(stage_surface, stage_rect)

        # 標題
        self.draw_title(screen, self.title, y=180, font=self.title_font)

        # 科普知識內容（自動換行）
        self._draw_wrapped_text(screen, self.content, center_x, 300)

        # 繼續按鈕
        self.continue_button.draw(screen)

        # 鍵盤提示
        hint = "按 Space 或 Enter 繼續"
        hint_surface = self.small_font.render(hint, True, TEXT_MUTED)
        hint_rect = hint_surface.get_rect(center=(center_x, 600))
        screen.blit(hint_surface, hint_rect)

        # 淡入淡出遮罩
        self.draw_fade_overlay(screen)

    def _draw_wrapped_text(self, screen: pygame.Surface, text: str, center_x: int, start_y: int):
        """繪製自動換行的文字"""
        line_height = 50
        chars_per_line = 28  # 每行字數

        # 中文字元換行
        lines = []
        current_line = ""

        for char in text:
            if len(current_line) >= chars_per_line:
                lines.append(current_line)
                current_line = char
            else:
                current_line += char
        if current_line:
            lines.append(current_line)

        # 繪製每行文字
        for i, line in enumerate(lines):
            surface = self.text_font.render(line, True, TEXT_SECONDARY)
            rect = surface.get_rect(center=(center_x, start_y + i * line_height))
            screen.blit(surface, rect)


# 四個關卡的介紹場景子類別
class Intro1Scene(IntroScene):
    """第一關介紹場景"""
    STAGE_NUMBER = 1


class Intro2Scene(IntroScene):
    """第二關介紹場景"""
    STAGE_NUMBER = 2


class Intro3Scene(IntroScene):
    """第三關介紹場景"""
    STAGE_NUMBER = 3


class Intro4Scene(IntroScene):
    """第四關介紹場景"""
    STAGE_NUMBER = 4
