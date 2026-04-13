#!/usr/bin/env python3
"""
触发 TeslaMate 更新并监听 MQTT 消息

这个脚本会：
1. 通过访问 TeslaMate API 触发车辆唤醒/更新
2. 然后监听 MQTT 消息，显示收到的所有保留消息和实时更新
"""

import paho.mqtt.client as mqtt
import time
import sys

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
CAR_ID = 1
TESLAMATE_URL = "http://localhost:4000"

# 存储接收到的消息
messages = {}
message_count = 0


def on_connect(client, userdata, flags, reason_code, properties):
    """连接回调"""
    if reason_code == 0:
        print(f"✓ 成功连接到 MQTT broker: {MQTT_BROKER}:{MQTT_PORT}")
        print(f"✓ 订阅主题: teslamate/cars/{CAR_ID}/#\n")
        client.subscribe(f"teslamate/cars/{CAR_ID}/#")
        print("=" * 80)
        print("📡 开始监听 MQTT 消息...")
        print("=" * 80)
        print()
    else:
        print(f"✗ 连接失败，错误码: {reason_code}")
        sys.exit(1)


def on_message(client, userdata, msg):
    """消息回调"""
    global message_count
    topic = msg.topic
    payload = msg.payload.decode('utf-8')
    
    # 提取主题的最后一部分
    topic_key = topic.split('/')[-1]
    
    # 检查是否是新消息还是更新
    is_new = topic_key not in messages
    messages[topic_key] = payload
    message_count += 1
    
    # 选择性地高亮显示重要消息
    important_topics = [
        'display_name', 'state', 'healthy',
        'plugged_in', 'charging_state', 'battery_level',
        'locked', 'sentry_mode', 'is_climate_on',
        'latitude', 'longitude'
    ]
    
    if topic_key in important_topics:
        emoji = get_emoji(topic_key, payload)
        status = "🆕" if is_new else "🔄"
        print(f"{status} {emoji} {topic_key:30s} = {payload}")
    else:
        status = "NEW" if is_new else "UPD"
        print(f"  [{status}] {topic_key:30s} = {payload}")


def get_emoji(key, value):
    """根据键和值返回合适的emoji"""
    emoji_map = {
        'display_name': '🚗',
        'state': '📍',
        'healthy': '💚' if value.lower() == 'true' else '❤️',
        'plugged_in': '🔌' if value.lower() == 'true' else '🔋',
        'charging_state': '⚡',
        'battery_level': '🔋',
        'locked': '🔒' if value.lower() == 'true' else '🔓',
        'sentry_mode': '👁️',
        'is_climate_on': '❄️',
        'latitude': '🌍',
        'longitude': '🌍',
    }
    return emoji_map.get(key, '  ')


def trigger_teslamate_update():
    """触发 TeslaMate 更新（通过访问网页）"""
    import subprocess
    try:
        print(f"🔄 使用 curl 访问 TeslaMate ({TESLAMATE_URL}) 以触发更新...")
        result = subprocess.run(
            ['curl', '-s', '-o', '/dev/null', '-w', '%{http_code}', TESLAMATE_URL],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0 and result.stdout == '200':
            print(f"✓ TeslaMate 响应成功 (HTTP {result.stdout})\n")
            return True
        else:
            print(f"⚠️  TeslaMate 响应: {result.stdout if result.stdout else '未知'}\n")
            return False
    except Exception as e:
        print(f"⚠️  无法访问 TeslaMate: {e}\n")
        return False


def main():
    print("=" * 80)
    print("🚗 TeslaMate MQTT 消息监听器")
    print("=" * 80)
    print(f"MQTT Broker: {MQTT_BROKER}:{MQTT_PORT}")
    print(f"车辆 ID: {CAR_ID}")
    print(f"TeslaMate: {TESLAMATE_URL}")
    print("=" * 80)
    print()
    
    # 尝试触发 TeslaMate 更新
    trigger_teslamate_update()
    
    # 创建 MQTT 客户端
    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id="teslamate_monitor"
    )
    
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        print("📡 正在连接到 MQTT broker...")
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        
        # 启动循环并监听
        client.loop_start()
        
        # 监听 30 秒
        duration = 30
        print(f"⏳ 监听 {duration} 秒... (按 Ctrl+C 提前退出)\n")
        
        for i in range(duration):
            time.sleep(1)
            if i == 5:
                # 5秒后显示统计
                print(f"\n📊 5秒统计: 收到 {message_count} 条消息，{len(messages)} 个不同主题\n")
        
        # 停止循环
        client.loop_stop()
        client.disconnect()
        
        # 显示最终统计
        print("\n" + "=" * 80)
        print("📊 监听完成")
        print("=" * 80)
        print(f"总共收到: {message_count} 条消息")
        print(f"不同主题: {len(messages)} 个")
        print()
        
        if messages:
            print("📋 所有收到的主题列表:")
            print("-" * 80)
            for i, (key, value) in enumerate(sorted(messages.items()), 1):
                print(f"{i:3d}. {key:35s} = {value[:50]}")
        else:
            print("❌ 没有收到任何 MQTT 消息")
            print()
            print("可能的原因:")
            print("  1. 车辆处于深度休眠，TeslaMate 还没有发布任何数据")
            print("  2. MQTT broker 没有保留消息（可能重启过）")
            print("  3. TeslaMate 的 MQTT 配置有问题")
            print()
            print("建议:")
            print("  • 在 Tesla APP 中唤醒车辆")
            print("  • 检查 TeslaMate 日志: docker logs teslamate-teslamate-1")
            print("  • 等待 1-2 分钟后重新运行此脚本")
        
        print("=" * 80)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  收到中断信号")
        print(f"📊 收到 {message_count} 条消息，{len(messages)} 个不同主题")
        client.loop_stop()
        client.disconnect()
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
