"""
通用繪製工具函數
提供預繪製漸層背景等效能優化功能
"""

import pygame
from ..config import SCREEN_WIDTH, SCREEN_HEIGHT


def create_gradient_surface(
    base_color: tuple,
    width: int = SCREEN_WIDTH,
    height: int = SCREEN_HEIGHT,
    start_color: tuple = (20, 25, 40),
    factor: float = 1.0
) -> pygame.Surface:
    """
    創建預繪製的漸層背景 Surface

    Args:
        base_color: 目標顏色 (RGB tuple)
        width: 寬度
        height: 高度
        start_color: 起始顏色 (預設深色)
        factor: 混合係數

    Returns:
        預繪製的 pygame.Surface
    """
    surface = pygame.Surface((width, height))

    for y in range(height):
        ratio = y / height
        r = int(start_color[0] + (base_color[0] - start_color[0]) * ratio * factor)
        g = int(start_color[1] + (base_color[1] - start_color[1]) * ratio * factor)
        b = int(start_color[2] + (base_color[2] - start_color[2]) * ratio * factor)
        # 確保顏色值在有效範圍內
        r = max(0, min(255, r))
        g = max(0, min(255, g))
        b = max(0, min(255, b))
        pygame.draw.line(surface, (r, g, b), (0, y), (width, y))

    return surface
