"""
動畫工具模組
提供 easing 函數、插值工具和計時器管理
"""

import math


# ==================== Easing 函數 ====================

def ease_linear(t: float) -> float:
    """線性"""
    return t


def ease_in_quad(t: float) -> float:
    """二次方緩入"""
    return t * t


def ease_out_quad(t: float) -> float:
    """二次方緩出"""
    return 1 - (1 - t) * (1 - t)


def ease_in_out_quad(t: float) -> float:
    """二次方緩入緩出"""
    if t < 0.5:
        return 2 * t * t
    else:
        return 1 - pow(-2 * t + 2, 2) / 2


def ease_out_cubic(t: float) -> float:
    """三次方緩出"""
    return 1 - pow(1 - t, 3)


def ease_in_out_cubic(t: float) -> float:
    """三次方緩入緩出"""
    if t < 0.5:
        return 4 * t * t * t
    else:
        return 1 - pow(-2 * t + 2, 3) / 2


def ease_out_elastic(t: float) -> float:
    """彈性緩出"""
    if t == 0:
        return 0
    if t == 1:
        return 1
    c4 = (2 * math.pi) / 3
    return pow(2, -10 * t) * math.sin((t * 10 - 0.75) * c4) + 1


def ease_out_back(t: float) -> float:
    """回彈緩出"""
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * pow(t - 1, 3) + c1 * pow(t - 1, 2)


def ease_out_bounce(t: float) -> float:
    """彈跳緩出"""
    n1 = 7.5625
    d1 = 2.75
    if t < 1 / d1:
        return n1 * t * t
    elif t < 2 / d1:
        t -= 1.5 / d1
        return n1 * t * t + 0.75
    elif t < 2.5 / d1:
        t -= 2.25 / d1
        return n1 * t * t + 0.9375
    else:
        t -= 2.625 / d1
        return n1 * t * t + 0.984375


# ==================== 插值工具 ====================

def lerp(start: float, end: float, t: float) -> float:
    """線性插值"""
    return start + (end - start) * t


def lerp_color(color1: tuple, color2: tuple, t: float) -> tuple:
    """顏色插值"""
    return tuple(int(lerp(c1, c2, t)) for c1, c2 in zip(color1, color2))


def lerp_clamped(start: float, end: float, t: float) -> float:
    """限制範圍的線性插值"""
    t = max(0.0, min(1.0, t))
    return lerp(start, end, t)


def smooth_damp(current: float, target: float, velocity: float,
               smooth_time: float, dt: float) -> tuple:
    """
    平滑阻尼（類似 Unity 的 SmoothDamp）
    返回 (new_value, new_velocity)
    """
    smooth_time = max(0.0001, smooth_time)
    omega = 2.0 / smooth_time
    x = omega * dt
    exp_factor = 1.0 / (1.0 + x + 0.48 * x * x + 0.235 * x * x * x)

    change = current - target
    temp = (velocity + omega * change) * dt
    velocity = (velocity - omega * temp) * exp_factor
    output = target + (change + temp) * exp_factor

    return output, velocity


# ==================== 動畫計時器 ====================

class AnimationTimer:
    """動畫計時器"""

    def __init__(self, duration: float, easing=ease_out_quad, loop: bool = False):
        self.duration = duration
        self.easing = easing
        self.loop = loop
        self.elapsed = 0.0
        self.is_playing = False
        self.is_finished = False
        self._on_complete = None

    def start(self):
        """開始動畫"""
        self.elapsed = 0.0
        self.is_playing = True
        self.is_finished = False

    def stop(self):
        """停止動畫"""
        self.is_playing = False

    def reset(self):
        """重置動畫"""
        self.elapsed = 0.0
        self.is_finished = False

    def update(self, dt: float) -> float:
        """
        更新計時器
        返回 easing 後的進度值 (0.0 ~ 1.0)
        """
        if not self.is_playing:
            return self.easing(min(1.0, self.elapsed / self.duration))

        self.elapsed += dt

        if self.elapsed >= self.duration:
            if self.loop:
                self.elapsed = self.elapsed % self.duration
            else:
                self.elapsed = self.duration
                self.is_playing = False
                self.is_finished = True
                if self._on_complete:
                    self._on_complete()

        t = min(1.0, self.elapsed / self.duration)
        return self.easing(t)

    def on_complete(self, callback):
        """設定完成回調"""
        self._on_complete = callback
        return self

    @property
    def progress(self) -> float:
        """取得原始進度 (0.0 ~ 1.0)"""
        return min(1.0, self.elapsed / self.duration)

    @property
    def value(self) -> float:
        """取得 easing 後的值"""
        return self.easing(self.progress)


class PulseAnimation:
    """脈動動畫（持續循環的正弦波動畫）"""

    def __init__(self, speed: float = 2.0, min_val: float = 0.0, max_val: float = 1.0):
        self.speed = speed
        self.min_val = min_val
        self.max_val = max_val
        self.phase = 0.0

    def update(self, dt: float) -> float:
        """更新並返回當前值"""
        self.phase += dt * self.speed
        # 使用正弦波產生 0~1 的值
        t = (math.sin(self.phase) + 1) / 2
        return lerp(self.min_val, self.max_val, t)

    def reset(self):
        """重置相位"""
        self.phase = 0.0


class ShineAnimation:
    """光澤動畫（從左到右的掃描效果）"""

    def __init__(self, duration: float = 2.0, width: float = 0.3):
        self.duration = duration
        self.width = width  # 光澤寬度 (0~1)
        self.position = -width  # 當前位置

    def update(self, dt: float):
        """更新位置"""
        self.position += dt / self.duration
        if self.position > 1.0 + self.width:
            self.position = -self.width

    def get_alpha_at(self, x: float) -> float:
        """
        取得指定位置的透明度
        x: 0.0 ~ 1.0 (元素寬度的比例)
        返回: 0.0 ~ 1.0
        """
        dist = abs(x - self.position)
        if dist > self.width:
            return 0.0
        return 1.0 - (dist / self.width)

    def reset(self):
        """重置位置"""
        self.position = -self.width


# ==================== 數值動畫 ====================

class ValueAnimator:
    """數值動畫器"""

    def __init__(self, initial_value: float = 0.0):
        self.current = initial_value
        self.target = initial_value
        self.velocity = 0.0
        self.smooth_time = 0.2

    def set_target(self, value: float, immediate: bool = False):
        """設定目標值"""
        self.target = value
        if immediate:
            self.current = value
            self.velocity = 0.0

    def update(self, dt: float) -> float:
        """更新並返回當前值"""
        self.current, self.velocity = smooth_damp(
            self.current, self.target, self.velocity, self.smooth_time, dt
        )
        return self.current

    @property
    def value(self) -> float:
        return self.current

    @property
    def is_animating(self) -> bool:
        return abs(self.current - self.target) > 0.001


class CountUpAnimator:
    """數字計數動畫"""

    def __init__(self, duration: float = 0.5, easing=ease_out_quad):
        self.duration = duration
        self.easing = easing
        self.start_value = 0
        self.end_value = 0
        self.current_value = 0
        self.elapsed = 0.0
        self.is_playing = False

    def animate_to(self, target: int, from_value: int = None):
        """開始動畫到目標值"""
        self.start_value = from_value if from_value is not None else self.current_value
        self.end_value = target
        self.elapsed = 0.0
        self.is_playing = True

    def update(self, dt: float) -> int:
        """更新並返回當前整數值"""
        if not self.is_playing:
            return self.current_value

        self.elapsed += dt
        if self.elapsed >= self.duration:
            self.elapsed = self.duration
            self.is_playing = False

        t = self.easing(self.elapsed / self.duration)
        self.current_value = int(lerp(self.start_value, self.end_value, t))
        return self.current_value

    @property
    def value(self) -> int:
        return self.current_value
