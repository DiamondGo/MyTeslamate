#!/usr/bin/env python3
"""
实时监听 Tesla 车辆 MQTT 消息

用于测试和监控车辆状态变化
"""

import paho.mqtt.client as mqtt
import sys
from datetime import datetime

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
CAR_ID = 1
MQTT_NAMESPACE = "teslamate"

# 存储之前的值，用于检测变化
previous_values = {}
message_count = 0


def get_timestamp():
    """获取当前时间戳"""
    return datetime.now().strftime("%H:%M:%S")


def get_emoji(topic_key, value):
    """根据主题返回合适的 emoji"""
    emoji_map = {
        'display_name': '🚗',
        'state': '📍',
        'healthy': '💚',
        'plugged_in': '🔌',
        'charging_state': '⚡',
        'charge_port_door_open': '🚪',
        'battery_level': '🔋',
        'usable_battery_level': '🔋',
        'charge_limit_soc': '🎯',
        'rated_battery_range_km': '📏',
        'est_battery_range_km': '📏',
        'latitude': '🌍',
        'longitude': '🌍',
        'speed': '🏃',
        'heading': '🧭',
        'odometer': '🛣️',
        'inside_temp': '🌡️',
        'outside_temp': '🌡️',
        'is_climate_on': '❄️',
        'climate_keeper_mode': '❄️',
        'locked': '🔒' if str(value).lower() == 'true' else '🔓',
        'sentry_mode': '👁️',
        'windows_open': '🪟',
        'doors_open': '🚪',
        'trunk_open': '📦',
        'frunk_open': '📦',
        'is_user_present': '👤',
        'shift_state': '⚙️',
        'power': '⚡',
        'is_preconditioning': '🔥',
        'driver_front_door_open': '🚪',
        'driver_rear_door_open': '🚪',
        'passenger_front_door_open': '🚪',
        'passenger_rear_door_open': '🚪',
        'center_display_state': '📱',
        'charger_power': '⚡',
    }
    return emoji_map.get(topic_key, '  ')


def on_connect(client, userdata, flags, reason_code, properties):
    """连接回调"""
    if reason_code == 0:
        topic = f"teslamate/{MQTT_NAMESPACE}/cars/{CAR_ID}/#"
        client.subscribe(topic)
        print("=" * 80)
        print(f"🚗 实时监听 Tesla 车辆 MQTT 消息")
        print("=" * 80)
        print(f"⏰ 开始时间: {get_timestamp()}")
        print(f"📡 MQTT Broker: {MQTT_BROKER}:{MQTT_PORT}")
        print(f"📌 订阅主题: {topic}")
        print("=" * 80)
        print("💡 提示: 现在可以通过 APP 操作车辆（如开启通风），观察消息变化")
        print("=" * 80)
        print()
    else:
        print(f"✗ 连接失败，错误码: {reason_code}")
        sys.exit(1)


def on_message(client, userdata, msg):
    """消息回调"""
    global message_count, previous_values
    
    topic = msg.topic
    payload = msg.payload.decode('utf-8')
    
    # 提取主题的最后一部分
    topic_key = topic.split('/')[-1]
    
    # 检查是否是新消息或值已改变
    is_new = topic_key not in previous_values
    is_changed = not is_new and previous_values[topic_key] != payload
    
    # 更新计数和存储
    message_count += 1
    old_value = previous_values.get(topic_key, None)
    previous_values[topic_key] = payload
    
    # 获取时间戳和 emoji
    timestamp = get_timestamp()
    emoji = get_emoji(topic_key, payload)
    
    # 根据消息类型显示不同的标记和颜色
    if is_new:
        # 新主题（首次收到）
        print(f"[{timestamp}] 🆕 {emoji} {topic_key:35s} = {payload}")
    elif is_changed:
        # 值发生变化（重要！）
        print(f"[{timestamp}] 🔄 {emoji} {topic_key:35s} = {payload:30s} (was: {old_value})")
        print("    " + "▲" * 40)  # 高亮标记
    else:
        # 值未变化（静默显示）
        # print(f"[{timestamp}]    {emoji} {topic_key:35s} = {payload}")
        pass  # 不显示未变化的消息，减少干扰


def on_disconnect(client, userdata, flags, reason_code, properties):
    """断开连接回调"""
    print()
    print("=" * 80)
    print(f"⚠️  MQTT 连接断开 (错误码: {reason_code})")
    print("=" * 80)


def main():
    # 创建 MQTT 客户端
    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id="tesla_live_monitor"
    )
    
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    
    try:
        # 连接到 broker
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        
        # 开始循环监听
        print("正在连接到 MQTT broker...\n")
        client.loop_forever()
        
    except KeyboardInterrupt:
        print("\n")
        print("=" * 80)
        print(f"⏹️  监听停止")
        print("=" * 80)
        print(f"📊 统计:")
        print(f"   总消息数: {message_count}")
        print(f"   不同主题: {len(previous_values)}")
        print(f"   结束时间: {get_timestamp()}")
        print("=" * 80)
        client.disconnect()
        sys.exit(0)
        
    except Exception as e:
        print(f"\n✗ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
