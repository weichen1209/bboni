"""
遊戲主程式
"""

import pygame
import sys
import os

# 添加專案根目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS, TITLE, BBONI_ADDRESS, FontManager
)
from .scenes.menu import MenuScene
from .scenes.calibration import CalibrationScene
from .scenes.result import ResultScene
from .scenes.stage1_material import MaterialStage
from .scenes.stage2_deposition import DepositionStage
from .scenes.stage3_exposure import ExposureStage
from .scenes.stage4_etching import EtchingStage
from .utils.cv_scoring import ShapeType
from sensor.bboni_ble import BboniSensor


class Game:
    """遊戲主類別"""

    def __init__(self):
        # 初始化 Pygame
        pygame.init()
        pygame.display.set_caption(TITLE)

        # 初始化字體管理器（效能優化：預載入所有字體）
        FontManager.init()

        # 設定視窗
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.running = True

        # 感測器
        self.sensor = None
        self._init_sensor()

        # 遊戲狀態
        self.scores = {
            "purity": 0,
            "uniformity": 0,
            "exposure": 0,
            "precision": 0,
        }

        # 選擇的圖形類型（在第三關選擇，第三、四關共用）
        self.selected_shape_type = ShapeType.TRANSISTOR

        # 場景管理
        self.scenes = {
            "menu": MenuScene,
            "calibration": CalibrationScene,
            "stage1": MaterialStage,
            "stage2": DepositionStage,
            "stage3": ExposureStage,
            "stage4": EtchingStage,
            "result": ResultScene,
        }
        self.current_scene = None
        self._switch_scene("menu")

    def _init_sensor(self):
        """初始化感測器"""
        try:
            self.sensor = BboniSensor(BBONI_ADDRESS)
            self.sensor.connect(blocking=False)
        except Exception:
            self.sensor = None

    def _switch_scene(self, scene_name: str):
        """切換場景"""
        if self.current_scene:
            self.current_scene.on_exit()

        if scene_name in self.scenes:
            self.current_scene = self.scenes[scene_name](self)
            self.current_scene.on_enter()

    def run(self):
        """遊戲主循環"""
        # Workaround for pygame joystick/controller bug (GitHub #4568)
        # First event.get() call may fail with connected controllers
        try:
            pygame.event.get()
        except (SystemError, KeyError):
            pass

        while self.running:
            dt = self.clock.tick(FPS) / 1000.0  # 轉換為秒

            # 處理事件
            try:
                events = pygame.event.get()
            except (SystemError, KeyError):
                # Retry once if pygame joystick bug occurs
                events = []
            for event in events:
                if event.type == pygame.QUIT:
                    self.running = False
                else:
                    if self.current_scene:
                        self.current_scene.handle_event(event)

            # 更新
            if self.current_scene:
                self.current_scene.update(dt)

                # 檢查場景切換
                if self.current_scene.finished:
                    next_scene = self.current_scene.next_scene
                    if next_scene:
                        self._switch_scene(next_scene)

            # 繪製
            if self.current_scene:
                self.current_scene.draw(self.screen)

            pygame.display.flip()

        self.quit()

    def quit(self):
        """退出遊戲"""
        if self.sensor:
            self.sensor.disconnect()
        pygame.quit()
        sys.exit()


def main():
    """主函數"""
    game = Game()
    game.run()


if __name__ == "__main__":
    main()
