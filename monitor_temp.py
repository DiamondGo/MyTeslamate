#!/usr/bin/env python3
"""
monitor_temp.py – 监控 Tesla 温度变化事件示例

演示三种用法：
  1. 只监控车内/车外温度
  2. 用 on_climate_change() 监控所有气候相关事件
  3. 在自己的类中嵌入监控逻辑

运行：
    /Users/kexie/source/teslamate/venv/bin/python monitor_temp.py
"""

import time
from tesla import TeslaMQTTClient, TeslaEvent, EventType
from config import MQTT_BROKER, MQTT_PORT, CAR_ID, MQTT_NAMESPACE


# ---------------------------------------------------------------------------
# 方式 1：只监控车内 / 车外温度（最简单）
# ---------------------------------------------------------------------------

def example_simple():
    """只监控 inside_temp 和 outside_temp 两个事件。"""

    def on_temp(event: TeslaEvent):
        # is_initial=True 表示这是连接时收到的 retained 初始值，不是实时变化
        tag = "[初始]" if event.is_initial else "[变化]"
        s = event.state  # 变化后的完整状态快照
        print(
            f"{tag} {event.timestamp.strftime('%H:%M:%S')}  "
            f"{event.event_type.name}: "
            f"{event.old_value} → {event.new_value} °C  "
            f"| 车内 {s.inside_temp}°C / 车外 {s.outside_temp}°C"
        )

    client = TeslaMQTTClient(
        broker=MQTT_BROKER,
        port=MQTT_PORT,
        car_id=CAR_ID,
        namespace=MQTT_NAMESPACE,
    )
    client.on(EventType.INSIDE_TEMP,  on_temp)   # 车内温度
    client.on(EventType.OUTSIDE_TEMP, on_temp)   # 车外温度

    with client:
        client.wait_for_initial_state(timeout=5)
        print(f"\n当前车内温度: {client.state.inside_temp} °C")
        print(f"当前车外温度: {client.state.outside_temp} °C\n")
        print("监控温度变化中，按 Ctrl+C 退出…\n")
        while True:
            time.sleep(1)


# ---------------------------------------------------------------------------
# 方式 2：用 on_climate_change() 监控所有气候相关事件
#         包括：温度、空调开关、预热、除霜、风扇、keeper mode 等共 10 个
# ---------------------------------------------------------------------------

def example_climate_group():
    """用分组快捷方法一次注册所有气候事件。"""

    def on_climate(event: TeslaEvent):
        if event.is_initial:
            return  # 忽略启动时的初始值，只关心实时变化
        print(
            f"[{event.timestamp.strftime('%H:%M:%S')}] "
            f"{event.event_type.name:30s}: "
            f"{event.old_value!r:15} → {event.new_value!r}"
        )

    client = TeslaMQTTClient(broker=MQTT_BROKER, port=MQTT_PORT, car_id=CAR_ID, namespace=MQTT_NAMESPACE)
    # on_climate_change 覆盖 EventType.climate_events() 中的全部 10 个事件：
    # INSIDE_TEMP, OUTSIDE_TEMP, IS_CLIMATE_ON, IS_PRECONDITIONING,
    # CLIMATE_KEEPER_MODE, DRIVER_TEMP_SETTING, PASSENGER_TEMP_SETTING,
    # FAN_STATUS, IS_REAR_DEFROSTER_ON, IS_FRONT_DEFROSTER_ON
    client.on_climate_change(on_climate)

    with client:
        client.wait_for_initial_state(timeout=5)
        s = client.state
        print(f"\n初始状态:")
        print(f"  车内温度:   {s.inside_temp} °C")
        print(f"  车外温度:   {s.outside_temp} °C")
        print(f"  空调:       {'开' if s.is_climate_on else '关'}")
        print(f"  预热中:     {s.is_preconditioning}")
        print(f"  Keeper模式: {s.climate_keeper_mode}")
        print("\n等待气候变化…\n")
        while True:
            time.sleep(1)


# ---------------------------------------------------------------------------
# 方式 3：在自己的类中嵌入监控逻辑（推荐用于实际项目）
# ---------------------------------------------------------------------------

class TempMonitor:
    """封装温度监控逻辑的示例类。"""

    def __init__(self):
        self.client = TeslaMQTTClient(broker=MQTT_BROKER, port=MQTT_PORT, car_id=CAR_ID, namespace=MQTT_NAMESPACE)
        # 注册感兴趣的事件
        self.client.on(EventType.INSIDE_TEMP,   self._on_inside_temp)
        self.client.on(EventType.OUTSIDE_TEMP,  self._on_outside_temp)
        self.client.on(EventType.IS_CLIMATE_ON, self._on_climate_toggle)
        self.client.on(EventType.IS_PRECONDITIONING, self._on_precondition)

    def _on_inside_temp(self, event: TeslaEvent):
        if event.is_initial:
            return
        old = event.old_value or 0
        new = event.new_value or 0
        delta = new - old
        arrow = "↑" if delta > 0 else "↓"
        print(f"  🌡️  车内温度 {arrow}  {old:.1f}°C → {new:.1f}°C  (Δ{delta:+.1f}°C)")

    def _on_outside_temp(self, event: TeslaEvent):
        if event.is_initial:
            return
        print(f"  🌤️  车外温度变化: {event.new_value}°C")

    def _on_climate_toggle(self, event: TeslaEvent):
        if event.is_initial:
            return
        if event.new_value:
            print("  ❄️  空调已开启")
        else:
            print("  ⏹️  空调已关闭")

    def _on_precondition(self, event: TeslaEvent):
        if event.is_initial:
            return
        if event.new_value:
            print("  🔥 预热（Preconditioning）已启动")
        else:
            print("  ✅ 预热已完成/停止")

    def run(self):
        with self.client:
            self.client.wait_for_initial_state(timeout=5)
            s = self.client.state
            print(f"\n初始状态 — 车内: {s.inside_temp}°C, 车外: {s.outside_temp}°C, 空调: {s.is_climate_on}")
            print("等待温度变化…\n")
            while True:
                time.sleep(1)


# ---------------------------------------------------------------------------
# 入口：默认运行方式 3（类封装版）
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    mode = sys.argv[1] if len(sys.argv) > 1 else "3"

    print("=" * 60)
    if mode == "1":
        print("方式 1：只监控车内/车外温度")
        print("=" * 60)
        example_simple()
    elif mode == "2":
        print("方式 2：监控所有气候相关事件")
        print("=" * 60)
        example_climate_group()
    else:
        print("方式 3：类封装版温度监控")
        print("=" * 60)
        TempMonitor().run()
