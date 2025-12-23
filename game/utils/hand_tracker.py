"""
MediaPipe 手部追蹤模組
用於 Stage 4 手繪電路關卡
"""

import cv2
import numpy as np
from typing import Optional, Tuple

try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False


class HandTracker:
    """MediaPipe 手部追蹤器"""

    # MediaPipe 手部標記索引
    INDEX_FINGER_TIP = 8
    THUMB_TIP = 4

    def __init__(self, camera_index: int = 0, width: int = 640, height: int = 480):
        """
        初始化手部追蹤器

        Args:
            camera_index: 攝影機索引
            width: 畫面寬度
            height: 畫面高度
        """
        self.camera_index = camera_index
        self.width = width
        self.height = height

        self.cap: Optional[cv2.VideoCapture] = None
        self.hands = None
        self.mp_hands = None
        self.mp_drawing = None

        # 當前幀數據
        self._current_frame: Optional[np.ndarray] = None
        self._hand_landmarks = None
        self._is_running = False

    def start(self) -> bool:
        """
        開啟 webcam 和 MediaPipe

        Returns:
            是否成功啟動
        """
        if not MEDIAPIPE_AVAILABLE:
            print("MediaPipe 未安裝，請執行: pip install mediapipe")
            return False

        # 開啟攝影機
        self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            print(f"無法開啟攝影機 {self.camera_index}")
            return False

        # 設定解析度
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)

        # 初始化 MediaPipe
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )

        self._is_running = True
        return True

    def stop(self):
        """關閉資源"""
        self._is_running = False

        if self.hands:
            self.hands.close()
            self.hands = None

        if self.cap:
            self.cap.release()
            self.cap = None

        self._current_frame = None
        self._hand_landmarks = None

    def update(self) -> bool:
        """
        更新一幀（每幀呼叫一次）

        Returns:
            是否成功更新
        """
        if not self._is_running or self.cap is None:
            return False

        ret, frame = self.cap.read()
        if not ret:
            return False

        # 鏡像翻轉（水平翻轉）
        frame = cv2.flip(frame, 1)

        # 轉換顏色空間給 MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # 執行手部偵測
        results = self.hands.process(rgb_frame)

        # 儲存結果
        self._current_frame = frame
        self._hand_landmarks = results.multi_hand_landmarks[0] if results.multi_hand_landmarks else None

        return True

    def get_frame(self) -> Optional[np.ndarray]:
        """
        取得當前鏡像後的 BGR 畫面

        Returns:
            BGR 格式的 numpy 陣列，或 None
        """
        return self._current_frame.copy() if self._current_frame is not None else None

    def get_index_finger_tip(self) -> Optional[Tuple[int, int]]:
        """
        取得食指指尖的像素座標

        Returns:
            (x, y) 座標元組，或 None（未偵測到手）
        """
        if self._hand_landmarks is None or self._current_frame is None:
            return None

        landmark = self._hand_landmarks.landmark[self.INDEX_FINGER_TIP]

        # 轉換為像素座標
        x = int(landmark.x * self._current_frame.shape[1])
        y = int(landmark.y * self._current_frame.shape[0])

        return (x, y)

    def get_thumb_tip(self) -> Optional[Tuple[int, int]]:
        """
        取得拇指指尖的像素座標

        Returns:
            (x, y) 座標元組，或 None
        """
        if self._hand_landmarks is None or self._current_frame is None:
            return None

        landmark = self._hand_landmarks.landmark[self.THUMB_TIP]

        x = int(landmark.x * self._current_frame.shape[1])
        y = int(landmark.y * self._current_frame.shape[0])

        return (x, y)

    def is_pinching(self, threshold: float = 40.0) -> bool:
        """
        判斷是否在捏合（拇指與食指距離小於閾值）

        Args:
            threshold: 判定捏合的距離閾值（像素）

        Returns:
            是否在捏合
        """
        index_tip = self.get_index_finger_tip()
        thumb_tip = self.get_thumb_tip()

        if index_tip is None or thumb_tip is None:
            return False

        distance = ((index_tip[0] - thumb_tip[0]) ** 2 +
                    (index_tip[1] - thumb_tip[1]) ** 2) ** 0.5

        return distance < threshold

    def has_hand(self) -> bool:
        """
        是否偵測到手

        Returns:
            是否有手部資料
        """
        return self._hand_landmarks is not None

    def draw_hand_landmarks(self, frame: np.ndarray) -> np.ndarray:
        """
        在畫面上繪製手部骨架

        Args:
            frame: BGR 格式的畫面

        Returns:
            繪製後的畫面
        """
        if self._hand_landmarks is None or not MEDIAPIPE_AVAILABLE:
            return frame

        self.mp_drawing.draw_landmarks(
            frame,
            self._hand_landmarks,
            self.mp_hands.HAND_CONNECTIONS,
            self.mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=3),
            self.mp_drawing.DrawingSpec(color=(255, 255, 255), thickness=2)
        )

        return frame

    @property
    def is_running(self) -> bool:
        """是否正在運行"""
        return self._is_running
