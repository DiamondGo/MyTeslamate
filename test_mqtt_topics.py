#!/usr/bin/env python3
"""
MQTT主题测试脚本

用于验证TeslaMate的MQTT主题是否正确，以及查看实时数据
"""

import paho.mqtt.client as mqtt
import sys
import time

from config import MQTT_BROKER, MQTT_PORT, CAR_ID


def on_connect(client, userdata, flags, reason_code, properties):
    """连接回调"""
    if reason_code == 0:
        print(f"✓ 成功连接到MQTT broker: {MQTT_BROKER}:{MQTT_PORT}")
        print("\n订阅所有TeslaMate主题...")
        # 订阅所有相关主题
        client.subscribe(f"teslamate/cars/{CAR_ID}/#")
        print(f"✓ 已订阅: teslamate/cars/{CAR_ID}/#")
        print("\n等待消息... (按 Ctrl+C 退出)\n")
        print("-" * 80)
    else:
        print(f"✗ 连接失败，错误码: {reason_code}")


def on_message(client, userdata, msg):
    """消息回调"""
    topic = msg.topic
    payload = msg.payload.decode('utf-8')
    
    # 高亮显示重要的主题
    important_topics = ['plugged_in', 'keep_accessory_power_on', 'charging_state']
    
    if any(important in topic for important in important_topics):
        print(f"⭐ {topic}")
        print(f"   值: {payload}")
        print("-" * 80)
    else:
        print(f"   {topic}: {payload}")


def main():
    print("=" * 80)
    print("TeslaMate MQTT 主题测试工具")
    print("=" * 80)
    print(f"MQTT Broker: {MQTT_BROKER}:{MQTT_PORT}")
    print(f"车辆 ID: {CAR_ID}")
    print("=" * 80)
    print()
    
    # 创建MQTT客户端
    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id="teslamate_topic_tester"
    )
    
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        print("正在连接...")
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n\n收到中断信号，正在退出...")
        client.disconnect()
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ 错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

