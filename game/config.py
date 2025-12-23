"""
遊戲配置
"""

import pygame

# 螢幕設定
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60
TITLE = "小小晶圓工程師 - 互動式半導體科普遊戲"

# 顏色定義
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (128, 128, 128)
LIGHT_GRAY = (200, 200, 200)
DARK_GRAY = (64, 64, 64)

# ==================== 新增：背景色系 ====================
BG_DARK = (12, 15, 25)              # 最深背景
BG_MEDIUM = (20, 28, 45)            # 面板背景
BG_LIGHT = (35, 45, 65)             # 浮起表面
BG_SURFACE = (45, 55, 80)           # 卡片、按鈕

# ==================== 新增：文字色系 ====================
TEXT_PRIMARY = (255, 255, 255)      # 主要文字
TEXT_SECONDARY = (180, 190, 210)    # 次要文字
TEXT_MUTED = (120, 130, 150)        # 提示文字
TEXT_HIGHLIGHT = (100, 220, 255)    # 高亮文字

# 半導體相關顏色
SILICON_BLUE = (70, 130, 180)       # 矽晶圓
POLYSILICON_GRAY = (105, 105, 105)  # 多晶矽
SAND_YELLOW = (237, 201, 175)       # 沙子
PHOTORESIST_PURPLE = (148, 0, 211)  # 光阻
WAFER_RAINBOW = [                   # 晶圓彩虹色
    (255, 0, 0),
    (255, 127, 0),
    (255, 255, 0),
    (0, 255, 0),
    (0, 0, 255),
    (75, 0, 130),
    (148, 0, 211),
]

# ==================== 新增：特效顏色 ====================
UV_PURPLE = (138, 43, 226)          # UV曝光
UV_PURPLE_GLOW = (180, 100, 255)    # UV光暈
PLASMA_CYAN = (0, 255, 255)         # 電漿/蝕刻
PLASMA_CYAN_DARK = (0, 180, 200)    # 電漿暗色
GLOW_BLUE = (85, 175, 235)          # 藍色光暈
GLOW_GREEN = (100, 255, 170)        # 綠色光暈
GOLD_BRIGHT = (255, 215, 60)        # 亮金色

# 主題色
PRIMARY_COLOR = (52, 152, 219)      # 主色調 (藍)
PRIMARY_LIGHT = (85, 175, 235)      # 主色調亮
PRIMARY_DARK = (35, 120, 180)       # 主色調暗
SECONDARY_COLOR = (46, 204, 113)    # 輔助色 (綠)
SECONDARY_LIGHT = (80, 230, 140)    # 輔助色亮
ACCENT_COLOR = (241, 196, 15)       # 強調色 (黃)
ACCENT_LIGHT = (255, 215, 60)       # 強調色亮
DANGER_COLOR = (231, 76, 60)        # 警告色 (紅)
DANGER_DARK = (180, 50, 40)         # 警告色暗

# ==================== 動畫常數 ====================
ANIMATION_FAST = 0.15               # 快速動畫 (按鈕hover)
ANIMATION_NORMAL = 0.3              # 一般動畫
ANIMATION_SLOW = 0.5                # 慢速動畫 (場景過渡)
ANIMATION_VERY_SLOW = 0.8           # 超慢動畫

# ==================== UI 常數 ====================
BUTTON_CORNER_RADIUS = 12           # 按鈕圓角
BUTTON_SHADOW_OFFSET = (3, 3)       # 按鈕陰影偏移
PROGRESSBAR_CORNER_RADIUS = 8       # 進度條圓角
PANEL_CORNER_RADIUS = 15            # 面板圓角

# bboni AI 設定
BBONI_ADDRESS = "E1:91:DC:E7:D5:61"
BBONI_SENSITIVITY = 2048  # 加速度計靈敏度 (LSB/g)

# 遊戲設定
CALIBRATION_SAMPLES = 50  # 校正取樣數
CALIBRATION_DELAY = 0.02  # 校正取樣間隔

# 評分權重
SCORE_WEIGHTS = {
    "purity": 25,       # 純度 (關卡1)
    "uniformity": 25,   # 均勻度 (關卡2)
    "exposure": 25,     # 曝光品質 (關卡3)
    "precision": 25,    # 蝕刻精度 (關卡4)
}


# ==================== 效能優化工具類別 ====================

class FontManager:
    """
    全域字體管理器（效能優化：避免重複載入字體）
    """
    _instance = None
    _fonts = {}
    _initialized = False

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def init(cls):
        """初始化字體管理器（需在 pygame.init() 之後呼叫）"""
        if cls._initialized:
            return
        cls._initialized = True
        # 預載入常用字體
        cls._fonts = {
            'title': pygame.font.SysFont("Microsoft JhengHei", 48),
            'large': pygame.font.SysFont("Microsoft JhengHei", 36),
            'medium': pygame.font.SysFont("Microsoft JhengHei", 24),
            'small': pygame.font.SysFont("Microsoft JhengHei", 18),
            'button': pygame.font.SysFont("Microsoft JhengHei", 32),
        }

    @classmethod
    def get(cls, name: str) -> pygame.font.Font:
        """取得字體"""
        if not cls._initialized:
            cls.init()
        return cls._fonts.get(name, cls._fonts['medium'])

    @classmethod
    def get_sized(cls, size: int) -> pygame.font.Font:
        """取得指定大小的字體（會快取）"""
        if not cls._initialized:
            cls.init()
        key = f'size_{size}'
        if key not in cls._fonts:
            cls._fonts[key] = pygame.font.SysFont("Microsoft JhengHei", size)
        return cls._fonts[key]


class TextCache:
    """
    文字渲染快取（效能優化：避免每幀重新渲染相同文字）
    """

    def __init__(self, max_size: int = 100):
        self._cache = {}
        self._max_size = max_size

    def render(self, font: pygame.font.Font, text: str, color: tuple) -> pygame.Surface:
        """
        渲染文字（使用快取）

        Args:
            font: pygame 字體物件
            text: 要渲染的文字
            color: 文字顏色

        Returns:
            渲染後的 Surface
        """
        # 建立快取 key
        key = (id(font), text, color)

        if key not in self._cache:
            # 清理過大的快取
            if len(self._cache) >= self._max_size:
                # 移除一半的快取項目
                keys_to_remove = list(self._cache.keys())[:self._max_size // 2]
                for k in keys_to_remove:
                    del self._cache[k]

            # 渲染並快取
            self._cache[key] = font.render(text, True, color)

        return self._cache[key]

    def clear(self):
        """清空快取"""
        self._cache.clear()


# 全域文字快取實例
text_cache = TextCache()
