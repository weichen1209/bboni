#!/usr/bin/env python3
"""
IMU 傾斜動作資料收集腳本
用於收集訓練資料，標記三種動作：往左傾斜、平放、往右傾斜
"""

import csv
import time
import sys
from datetime import datetime
from sensor.bboni_ble import BboniSensor

# 動作標籤定義
ACTIONS = {
    '1': 'tilt_left',    # 往左傾斜
    '2': 'flat',         # 平放
    '3': 'tilt_right',   # 往右傾斜
}

def print_menu():
    """顯示動作選單"""
    print("\n" + "=" * 50)
    print("請選擇要記錄的動作：")
    print("  1 - 往左傾斜 (tilt_left)")
    print("  2 - 平放 (flat)")
    print("  3 - 往右傾斜 (tilt_right)")
    print("  q - 結束收集")
    print("=" * 50)

def collect_samples(sensor: BboniSensor, label: str, duration: float = 3.0, sample_rate: float = 0.02):
    """
    收集指定動作的樣本
    
    Args:
        sensor: BboniSensor 實例
        label: 動作標籤
        duration: 收集時間（秒）
        sample_rate: 取樣間隔（秒）
    
    Returns:
        list: 收集到的樣本列表
    """
    samples = []
    start_time = time.time()
    
    print(f"\n開始收集 [{label}] 資料，請保持動作 {duration} 秒...")
    print("3...")
    time.sleep(1)
    print("2...")
    time.sleep(1)
    print("1...")
    time.sleep(1)
    print("開始！")
    
    collect_start = time.time()
    while time.time() - collect_start < duration:
        # 取得原始 IMU 資料
        raw_data = sensor.get_raw_imu_data()
        # 取得校正後的 IMU 資料
        calibrated_data = sensor.get_imu_data()
        # 取得傾斜角度
        roll, pitch = sensor.get_tilt_angle()
        
        sample = {
            'timestamp': datetime.now().isoformat(),
            'label': label,
            # 原始加速度計資料
            'raw_ax': raw_data.ax,
            'raw_ay': raw_data.ay,
            'raw_az': raw_data.az,
            # 原始陀螺儀資料
            'raw_gx': raw_data.gx,
            'raw_gy': raw_data.gy,
            'raw_gz': raw_data.gz,
            # 校正後加速度計資料
            'cal_ax': calibrated_data.ax,
            'cal_ay': calibrated_data.ay,
            'cal_az': calibrated_data.az,
            # 校正後陀螺儀資料
            'cal_gx': calibrated_data.gx,
            'cal_gy': calibrated_data.gy,
            'cal_gz': calibrated_data.gz,
            # 傾斜角度
            'roll': roll,
            'pitch': pitch,
            # 加速度 g 值
            'accel_g_x': calibrated_data.accel_g()[0],
            'accel_g_y': calibrated_data.accel_g()[1],
            'accel_g_z': calibrated_data.accel_g()[2],
        }
        samples.append(sample)
        
        # 顯示即時數據
        elapsed = time.time() - collect_start
        print(f"\r  [{elapsed:.1f}s] roll={roll:+.1f}° pitch={pitch:+.1f}° ax={raw_data.ax:+6d} ay={raw_data.ay:+6d} az={raw_data.az:+6d}", end="")
        
        time.sleep(sample_rate)
    
    print(f"\n完成！收集了 {len(samples)} 筆資料")
    return samples

def save_to_csv(samples: list, filename: str):
    """將樣本儲存到 CSV 檔案"""
    if not samples:
        return
    
    fieldnames = samples[0].keys()
    
    # 檢查檔案是否存在，決定是否寫入標題
    try:
        with open(filename, 'r') as f:
            file_exists = True
    except FileNotFoundError:
        file_exists = False
    
    with open(filename, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerows(samples)

def main():
    # 產生輸出檔名
    output_file = f"training_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    print("=" * 50)
    print("IMU 傾斜動作資料收集工具")
    print("=" * 50)
    print(f"輸出檔案: {output_file}")
    
    # 連接感測器
    print("\n正在連接 bboni AI 感測器...")
    sensor = BboniSensor()
    
    if not sensor.connect(blocking=True):
        print("錯誤：無法連接感測器！")
        print("請確認：")
        print("  1. 裝置已開啟")
        print("  2. 藍牙已啟用")
        print("  3. 裝置地址正確")
        sys.exit(1)
    
    print("連接成功！")
    
    # 校正感測器
    print("\n請將裝置平放，準備進行校正...")
    input("按 Enter 開始校正...")
    print("校正中，請保持裝置靜止...")
    
    if sensor.calibrate(samples=100, delay=0.02):
        print("校正完成！")
    else:
        print("校正失敗！")
        sensor.disconnect()
        sys.exit(1)
    
    # 開始收集資料
    all_samples = []
    
    try:
        while True:
            print_menu()
            choice = input("請輸入選項: ").strip().lower()
            
            if choice == 'q':
                break
            
            if choice not in ACTIONS:
                print("無效的選項，請重新輸入")
                continue
            
            label = ACTIONS[choice]
            
            # 詢問收集時間
            try:
                duration = float(input(f"收集時間（秒，預設 3）: ").strip() or "3")
            except ValueError:
                duration = 3.0
            
            input(f"準備好後按 Enter 開始收集 [{label}] 資料...")
            
            samples = collect_samples(sensor, label, duration=duration)
            all_samples.extend(samples)
            
            # 即時儲存
            save_to_csv(samples, output_file)
            print(f"已儲存到 {output_file}")
            
            # 顯示統計
            label_counts = {}
            for s in all_samples:
                lbl = s['label']
                label_counts[lbl] = label_counts.get(lbl, 0) + 1
            
            print("\n目前收集統計：")
            for lbl, count in sorted(label_counts.items()):
                print(f"  {lbl}: {count} 筆")
            print(f"  總計: {len(all_samples)} 筆")
    
    except KeyboardInterrupt:
        print("\n\n收到中斷訊號...")
    
    finally:
        # 斷開連接
        print("\n正在斷開感測器連接...")
        sensor.disconnect()
        print("已斷開連接")
        
        if all_samples:
            print(f"\n資料已儲存至: {output_file}")
            print(f"總共收集了 {len(all_samples)} 筆資料")
        else:
            print("\n未收集任何資料")

if __name__ == "__main__":
    main()
