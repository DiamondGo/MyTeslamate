#!/Users/kexie/source/teslamate/venv/bin/python
"""
快速获取TeslaMate MQTT当前状态

这个脚本连接到MQTT broker并收集所有保留的消息，然后显示车辆状态
"""

import paho.mqtt.client as mqtt
import time
import sys

import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import MQTT_BROKER, MQTT_PORT, CAR_ID, MQTT_NAMESPACE

# 存储接收到的消息
messages = {}
connected = False


def on_connect(client, userdata, flags, reason_code, properties):
    """连接回调"""
    global connected
    if reason_code == 0:
        print(f"✓ 成功连接到 MQTT broker: {MQTT_BROKER}:{MQTT_PORT}")
        connected = True
        # 订阅所有TeslaMate主题
        # TeslaMate 发布路径格式: teslamate/{MQTT_NAMESPACE}/cars/{id}/...
        # docker-compose.yml 中 MQTT_NAMESPACE=teslamate，所以完整路径为 teslamate/teslamate/cars/1/...
        topic = f"teslamate/{MQTT_NAMESPACE}/cars/{CAR_ID}/#"
        client.subscribe(topic)
        print(f"✓ 已订阅: {topic}")
        print("\n正在收集消息...\n")
    else:
        print(f"✗ 连接失败，错误码: {reason_code}")
        sys.exit(1)


def on_message(client, userdata, msg):
    """消息回调"""
    topic = msg.topic
    payload = msg.payload.decode('utf-8')
    
    # 提取主题的最后一部分作为键
    topic_key = topic.split('/')[-1]
    messages[topic_key] = payload


def main():
    print("=" * 80)
    print("TeslaMate MQTT 状态查询工具")
    print("=" * 80)
    print(f"MQTT Broker: {MQTT_BROKER}:{MQTT_PORT}")
    print(f"车辆 ID: {CAR_ID}")
    print("=" * 80)
    print()
    
    # 创建MQTT客户端
    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id="teslamate_status_getter"
    )
    
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        print("正在连接...")
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        
        # 启动网络循环
        client.loop_start()
        
        # 等待连接和消息接收
        timeout = 5
        start_time = time.time()
        
        while not connected and (time.time() - start_time) < timeout:
            time.sleep(0.1)
        
        if not connected:
            print("✗ 连接超时")
            sys.exit(1)
        
        # 等待接收消息
        print("等待 3 秒以接收所有消息...")
        time.sleep(3)
        
        client.loop_stop()
        client.disconnect()
        
        # 显示结果
        print("\n" + "=" * 80)
        print("收到的车辆状态信息")
        print("=" * 80)
        
        if not messages:
            print("\n❌ 没有收到任何MQTT消息")
            print("\n可能的原因:")
            print("  1. 车辆处于休眠状态，TeslaMate 暂停了轮询（最常见）")
            print("  2. Mosquitto 重启后丢失了 retained 消息（未配置 persistence）")
            print("  3. TeslaMate 尚未完成首次车辆数据轮询")
            print("  4. MQTT_NAMESPACE 配置不匹配（当前订阅: teslamate/cars/1/#）")
            print("\n建议:")
            print("  • 在 Tesla APP 中操作车辆（开空调/锁车）以唤醒它")
            print("  • 访问 http://localhost:4000 查看 TeslaMate 显示的车辆状态")
            print("  • 等待 1-2 分钟后重试（TeslaMate 检测到车辆唤醒后会自动发布）")
            print("  • 检查 docker compose logs teslamate 确认是否有 car_id=1 的轮询日志")
        else:
            print(f"\n📊 收到 {len(messages)} 个主题的数据:\n")
            
            # 重要字段列表
            important_keys = [
                'display_name', 'state', 'healthy',
                'plugged_in', 'charging_state', 'charge_port_door_open',
                'battery_level', 'usable_battery_level', 'charge_limit_soc',
                'est_battery_range_km', 'rated_battery_range_km',
                'latitude', 'longitude', 'speed', 'heading',
                'odometer', 'elevation',
                'inside_temp', 'outside_temp', 'is_climate_on',
                'locked', 'sentry_mode', 'windows_open',
                'doors_open', 'trunk_open', 'frunk_open'
            ]
            
            # 先显示重要字段
            print("🔑 关键信息:")
            print("-" * 80)
            for key in important_keys:
                if key in messages:
                    value = messages[key]
                    # 添加emoji图标
                    emoji = get_emoji(key, value)
                    print(f"  {emoji} {key:30s} = {value}")
            
            # 显示其他字段
            other_messages = {k: v for k, v in messages.items() if k not in important_keys}
            if other_messages:
                print("\n📋 其他信息:")
                print("-" * 80)
                for key, value in sorted(other_messages.items()):
                    print(f"  • {key:30s} = {value}")
        
        print("\n" + "=" * 80)
        
    except KeyboardInterrupt:
        print("\n\n收到中断信号，正在退出...")
        client.disconnect()
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def get_emoji(key, value):
    """根据键和值返回合适的emoji"""
    emoji_map = {
        'display_name': '🚗',
        'state': '📍',
        'healthy': '💚' if value.lower() == 'true' else '❤️',
        'plugged_in': '🔌' if value.lower() == 'true' else '🔋',
        'charging_state': '⚡',
        'charge_port_door_open': '🚪',
        'battery_level': '🔋',
        'usable_battery_level': '🔋',
        'charge_limit_soc': '🎯',
        'est_battery_range_km': '📏',
        'rated_battery_range_km': '📏',
        'latitude': '🌍',
        'longitude': '🌍',
        'speed': '🏃',
        'heading': '🧭',
        'odometer': '🛣️',
        'elevation': '⛰️',
        'inside_temp': '🌡️',
        'outside_temp': '🌡️',
        'is_climate_on': '❄️',
        'locked': '🔒' if value.lower() == 'true' else '🔓',
        'sentry_mode': '👁️',
        'windows_open': '🪟',
        'doors_open': '🚪',
        'trunk_open': '📦',
        'frunk_open': '📦'
    }
    return emoji_map.get(key, '  ')


if __name__ == "__main__":
    main()
