"""
bboni AI BLE 連接模組
功能：透過藍牙連接 bboni AI 並讀取 IMU 數據
"""

import asyncio
import struct
import threading
import time
from dataclasses import dataclass
from typing import Optional
from bleak import BleakClient, BleakScanner


@dataclass
class IMUData:
    """IMU 感測器數據"""
    # 加速度計 (單位: LSB, 可轉換為 g)
    ax: int = 0
    ay: int = 0
    az: int = 0
    # 陀螺儀 (單位: LSB, 可轉換為 dps)
    gx: int = 0
    gy: int = 0
    gz: int = 0
    # 時間戳
    timestamp: int = 0

    def accel_g(self, sensitivity: int = 2048) -> tuple:
        """
        將加速度轉換為 g 值
        sensitivity: LSB/g (預設 2048 對應實際硬體設定)
        """
        return (
            self.ax / sensitivity,
            self.ay / sensitivity,
            self.az / sensitivity
        )

    def gyro_dps(self, sensitivity: float = 16.4) -> tuple:
        """
        將角速度轉換為 dps (度/秒)
        sensitivity: LSB/dps (預設 16.4 對應 ±2000 dps 範圍)
        """
        return (
            self.gx / sensitivity,
            self.gy / sensitivity,
            self.gz / sensitivity
        )


class BboniSensor:
    """bboni AI 感測器類別"""

    # BLE 地址 (可在初始化時覆蓋)
    DEFAULT_ADDRESS = "E1:91:DC:E7:D5:61"

    # IMU 數據特徵 UUID
    IMU_CHAR_UUIDS = [
        "00001601-0000-1000-8000-00805f9b34fb",  # 加速度計數據
        "00001603-0000-1000-8000-00805f9b34fb",  # 陀螺儀數據
    ]

    def __init__(self, address: str = None):
        """
        初始化 bboni AI 感測器
        address: BLE 地址，None 則使用預設值
        """
        self.address = address or self.DEFAULT_ADDRESS
        self.client: Optional[BleakClient] = None
        self.is_connected = False

        # IMU 數據
        self.imu_data = IMUData()
        self._lock = threading.Lock()

        # 校正偏移值
        self.calibration_offset = IMUData()

        # 原始未校正數據
        self._raw_imu_data = IMUData()

        # 異步事件循環
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False

        # 搖晃偵測（多層過濾法）
        self._prev_accel = None      # 上一筆加速度數據
        self._delta_buffer = []      # 變化率緩衝區
        self._delta_buffer_size = 20 # 緩衝區大小（減少以加快穩定恢復）
        self._last_intensity = 0.0   # 緩存上次計算結果
        self._quiet_count = 0        # 連續靜止計數器（用於快速恢復）

        # 傾斜角度校正（中立位置）
        self.neutral_roll = 0.0
        self.neutral_pitch = 0.0

        # 傾斜角度過濾（用於過濾原始角度跳動）
        self._last_raw_roll = None
        self._last_raw_pitch = None

        # 緩存最後一次有效的傾斜角度（避免回傳 0）
        self._last_valid_tilt = (0.0, 0.0)

        # EMA 濾波器（用於平滑加速度數據）
        self._filtered_accel = [0.0, 0.0, 0.0]  # [ax, ay, az]
        self._ema_alpha = 0.15  # 平滑係數（越小越平滑）
        self._ema_initialized = False

    def _notification_handler(self, sender, data: bytearray):
        """處理 BLE 通知數據"""
        with self._lock:
            # 根據 sender UUID 判斷數據類型
            sender_uuid = str(sender.uuid).lower()
            is_accel = "1601" in sender_uuid  # 加速度計特徵 UUID 包含 1601

            # 根據封包類型解析數據（加速度計有 1 byte header）
            if is_accel and len(data) >= 11:
                # 加速度計封包 (18 bytes)：跳過第一個 byte (0xff header)
                values = struct.unpack('<3h', data[1:7])
                timestamp = struct.unpack('<I', data[7:11])[0]
            elif not is_accel and len(data) >= 10:
                # 陀螺儀封包 (16 bytes)：無 header
                values = struct.unpack('<3h', data[:6])
                timestamp = struct.unpack('<I', data[6:10])[0]
            else:
                return  # 封包長度不足，跳過

            # 數據驗證：拒絕超出範圍的數據（±2g = ±32768 LSB）
            MAX_VALID_LSB = 32768
            if any(abs(v) > MAX_VALID_LSB for v in values):
                return  # 拒絕異常封包

            if is_accel:
                # 保存原始數據（用於 debug 和校正）
                self._raw_imu_data.ax = values[0]
                self._raw_imu_data.ay = values[1]
                self._raw_imu_data.az = values[2]
                self._raw_imu_data.timestamp = timestamp

                # EMA 濾波：平滑加速度數據
                if not self._ema_initialized:
                    self._filtered_accel = list(values)
                    self._ema_initialized = True
                else:
                    for i in range(3):
                        self._filtered_accel[i] = (
                            self._ema_alpha * values[i] +
                            (1 - self._ema_alpha) * self._filtered_accel[i]
                        )

                # 套用校正偏移到濾波後的數據
                self.imu_data.ax = int(self._filtered_accel[0]) - self.calibration_offset.ax
                self.imu_data.ay = int(self._filtered_accel[1]) - self.calibration_offset.ay
                self.imu_data.az = int(self._filtered_accel[2]) - self.calibration_offset.az
            else:
                # 陀螺儀數據
                self._raw_imu_data.gx = values[0]
                self._raw_imu_data.gy = values[1]
                self._raw_imu_data.gz = values[2]
                # 套用校正偏移
                self.imu_data.gx = values[0] - self.calibration_offset.gx
                self.imu_data.gy = values[1] - self.calibration_offset.gy
                self.imu_data.gz = values[2] - self.calibration_offset.gz

            self.imu_data.timestamp = timestamp

    async def _connect_async(self):
        """非同步連接"""
        self.client = BleakClient(self.address, timeout=30)
        await self.client.connect()
        self.is_connected = self.client.is_connected

        if self.is_connected:
            # 訂閱 IMU 數據通知
            for uuid in self.IMU_CHAR_UUIDS:
                try:
                    await self.client.start_notify(uuid, self._notification_handler)
                except Exception:
                    pass

    async def _disconnect_async(self):
        """非同步斷開連接"""
        if self.client and self.client.is_connected:
            for uuid in self.IMU_CHAR_UUIDS:
                try:
                    await self.client.stop_notify(uuid)
                except:
                    pass
            await self.client.disconnect()
        self.is_connected = False

    def _run_event_loop(self):
        """在背景執行緒運行事件迴圈"""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        try:
            self._loop.run_until_complete(self._connect_async())

            # 保持連接狀態
            while self._running and self.is_connected:
                self._loop.run_until_complete(asyncio.sleep(0.1))

        except (asyncio.TimeoutError, Exception):
            pass
        finally:
            self._loop.run_until_complete(self._disconnect_async())
            self._loop.close()

    def connect(self, blocking: bool = False) -> bool:
        """
        連接 bboni AI
        blocking: True 則阻塞直到連接完成
        """
        if self._running:
            return self.is_connected

        self._running = True
        self._thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self._thread.start()

        if blocking:
            # 等待連接
            timeout = 10
            start = time.time()
            while not self.is_connected and time.time() - start < timeout:
                time.sleep(0.1)

        return self.is_connected

    def disconnect(self):
        """斷開連接"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        self.is_connected = False

    def get_imu_data(self) -> IMUData:
        """取得當前 IMU 數據 (已校正，複製)"""
        with self._lock:
            return IMUData(
                ax=self.imu_data.ax,
                ay=self.imu_data.ay,
                az=self.imu_data.az,
                gx=self.imu_data.gx,
                gy=self.imu_data.gy,
                gz=self.imu_data.gz,
                timestamp=self.imu_data.timestamp
            )

    def get_raw_imu_data(self) -> IMUData:
        """取得原始未校正的 IMU 數據 (複製)"""
        with self._lock:
            return IMUData(
                ax=self._raw_imu_data.ax,
                ay=self._raw_imu_data.ay,
                az=self._raw_imu_data.az,
                gx=self._raw_imu_data.gx,
                gy=self._raw_imu_data.gy,
                gz=self._raw_imu_data.gz,
                timestamp=self._raw_imu_data.timestamp
            )

    def calibrate(self, samples: int = 100, delay: float = 0.02) -> bool:
        """
        校正感測器 (使用中位數作為零點偏移，對異常值更穩健)
        samples: 取樣數量
        delay: 取樣間隔 (秒)
        返回: 是否成功
        """
        if not self.is_connected:
            return False

        # 重置 EMA 濾波器
        self._ema_initialized = False
        self._filtered_accel = [0.0, 0.0, 0.0]

        # 重置偏移量
        self.calibration_offset = IMUData()

        # 收集樣本（分開儲存，以便使用中位數）
        ax_samples, ay_samples, az_samples = [], [], []
        gx_samples, gy_samples, gz_samples = [], [], []

        for _ in range(samples):
            data = self.get_raw_imu_data()

            # 只收集看起來合理的加速度樣本（總向量接近 1g = 2048 LSB）
            total = (data.ax**2 + data.ay**2 + data.az**2) ** 0.5
            if 1500 < total < 2600:  # 大約 0.73g ~ 1.27g，合理範圍（基於 2048 LSB/g）
                ax_samples.append(data.ax)
                ay_samples.append(data.ay)
                az_samples.append(data.az)

            # 陀螺儀樣本（靜止時應接近 0）
            gx_samples.append(data.gx)
            gy_samples.append(data.gy)
            gz_samples.append(data.gz)
            time.sleep(delay)

        # 使用中位數（對異常值更穩健）
        if ax_samples:
            n = len(ax_samples)
            self.calibration_offset.ax = sorted(ax_samples)[n // 2]
            self.calibration_offset.ay = sorted(ay_samples)[n // 2]
            self.calibration_offset.az = sorted(az_samples)[n // 2]

        n = len(gx_samples)
        if n > 0:
            self.calibration_offset.gx = sorted(gx_samples)[n // 2]
            self.calibration_offset.gy = sorted(gy_samples)[n // 2]
            self.calibration_offset.gz = sorted(gz_samples)[n // 2]

        # 校正後清除搖晃偵測緩衝區
        self._prev_accel = None
        self._delta_buffer.clear()
        self._quiet_count = 0

        # 重置原始角度過濾器
        self._last_raw_roll = None
        self._last_raw_pitch = None

        # 重置傾斜角度緩存
        self._last_valid_tilt = (0.0, 0.0)

        # 計算並儲存中立角度（用於傾斜校正）
        self.neutral_roll, self.neutral_pitch = self._calculate_raw_tilt_angle()

        return True

    def get_shake_intensity(self) -> float:
        """
        取得搖晃強度
        返回: 0.0（靜止）到 1.0（劇烈搖晃）

        使用多層過濾法（配合 16384 LSB/g 靈敏度）：
        1. 跳過相同數據（BLE 未更新時）
        2. 異常值過濾（> 1.5g 視為感測器錯誤）
        3. 單次雜訊過濾（< 0.15g 視為雜訊，連續 5 筆清空緩衝區）
        4. 滑動平均（50 筆）
        5. 死區過濾（< 0.2g 視為靜止）
        """
        import math
        # 使用原始數據計算搖晃（避免 EMA 濾波削弱訊號）
        data = self.get_raw_imu_data()

        # 檢查數據是否有效（使用三軸向量總和，基於 2048 LSB/g）
        total = math.sqrt(data.ax**2 + data.ay**2 + data.az**2)
        if total < 1000:  # 約 0.49g
            return 0.0

        # 當前加速度（原始 LSB 值）
        current = (data.ax, data.ay, data.az)

        # 第一層：如果數據完全相同，返回緩存結果（BLE 尚未更新）
        if self._prev_accel is not None:
            if current == self._prev_accel:
                return self._last_intensity

            # 計算歐幾里得距離
            delta = sum((c - p) ** 2 for c, p in zip(current, self._prev_accel)) ** 0.5
            # 正規化：除以靈敏度換算成 g 的變化（2048 LSB/g）
            delta_g = delta / 2048.0

            # 第二層：異常值過濾 - 單次變化超過 1.5g 視為感測器錯誤（±2g 範圍）
            if delta_g > 1.5:
                # 異常數據：仍更新 prev_accel，讓下次比較從這裡開始
                self._prev_accel = current
                return self._last_intensity

            # 第三層：單次變化太小視為雜訊（0.15g 閾值）
            if delta_g < 0.15:
                delta_g = 0.0
                self._quiet_count += 1
                # 連續 5 筆靜止讀數，清空緩衝區以快速恢復
                if self._quiet_count >= 5:
                    self._delta_buffer.clear()
                    self._quiet_count = 0
            else:
                self._quiet_count = 0  # 有動作，重置計數器
        else:
            delta_g = 0.0

        # 更新上一筆數據
        self._prev_accel = current

        # 第四層：滑動平均濾波
        self._delta_buffer.append(delta_g)
        if len(self._delta_buffer) > self._delta_buffer_size:
            self._delta_buffer.pop(0)

        avg_delta = sum(self._delta_buffer) / len(self._delta_buffer)

        # 第四層：死區過濾（放寬門檻讓靜止更容易被判定）
        if avg_delta < 0.3:
            self._last_intensity = 0.0
            return 0.0

        # 正規化到 0-1 範圍（0.3~0.6g 映射到 0~1）
        intensity = min(1.0, (avg_delta - 0.3) / 0.3)
        self._last_intensity = intensity
        return intensity

    def _angle_diff(self, a: float, b: float) -> float:
        """計算兩個角度的最短差異（處理 ±180° 環繞）"""
        diff = a - b
        while diff > 180:
            diff -= 360
        while diff < -180:
            diff += 360
        return diff

    def _calculate_raw_tilt_angle(self) -> tuple:
        """
        計算原始傾斜角度（不減去中立值，但過濾異常跳動）
        返回: (roll, pitch) 角度（度），若數據無效則返回 (0, 0)
        """
        import math
        data = self.get_raw_imu_data()

        # 檢查數據是否有效（使用三軸向量總和）
        # 無論裝置如何擺放，總加速度應該接近 1g (~2048 LSB)
        total = math.sqrt(data.ax**2 + data.ay**2 + data.az**2)
        if total < 1000:  # 總向量太小，數據無效
            return (0.0, 0.0)

        # 轉換為 g 值 (靈敏度: 2048 LSB/g, ±16g 範圍)
        ax = data.ax / 2048.0
        ay = data.ay / 2048.0
        az = data.az / 2048.0

        # 避免除以零
        if az == 0:
            az = 0.001

        # 裝置平放時（螢幕朝上），Z 軸接收重力
        # Roll: 左右傾斜（X 軸相對於 Z 軸）
        # Pitch: 前後傾斜（Y 軸相對於 Z 軸）
        roll = math.atan2(ax, az) * 180 / math.pi
        pitch = math.atan2(ay, az) * 180 / math.pi

        return roll, pitch

    def get_tilt_angle(self) -> tuple:
        """
        取得傾斜角度（相對於校正時的中立位置）
        返回: (roll, pitch) 角度（度），若數據無效則返回上次的有效值
        """
        raw_roll, raw_pitch = self._calculate_raw_tilt_angle()

        # 若數據無效，返回上次的有效值
        if raw_roll == 0.0 and raw_pitch == 0.0:
            return self._last_valid_tilt

        # 使用最短路徑計算相對於中立位置的角度
        rel_roll = self._angle_diff(raw_roll, self.neutral_roll)
        rel_pitch = self._angle_diff(raw_pitch, self.neutral_pitch)

        # 緩存有效值
        self._last_valid_tilt = (rel_roll, rel_pitch)

        return rel_roll, rel_pitch
