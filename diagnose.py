#!/usr/bin/env python3
"""
诊断脚本 - 检查TeslaMate MQTT消息
"""

import paho.mqtt.client as mqtt
import time
import sys
from datetime import datetime

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
CAR_ID = 1

received_messages = {}
last_update_time = {}

def on_connect(client, userdata, flags, reason_code, properties):
    """连接回调"""
    if reason_code == 0:
        print("=" * 80)
        print(f"✓ 成功连接到MQTT broker: {MQTT_BROKER}:{MQTT_PORT}")
        print("=" * 80)
        print(f"订阅所有TeslaMate主题: teslamate/cars/{CAR_ID}/#")
        print("=" * 80)
        print(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        print("\n等待TeslaMate消息... (按 Ctrl+C 退出)\n")
        
        # 订阅所有主题
        client.subscribe(f"teslamate/cars/{CAR_ID}/#")
    else:
        print(f"✗ 连接失败，错误码: {reason_code}")
        sys.exit(1)


def on_message(client, userdata, msg):
    """消息回调"""
    topic = msg.topic
    payload = msg.payload.decode('utf-8')
    now = datetime.now().strftime('%H:%M:%S')
    
    # 记录消息
    received_messages[topic] = payload
    last_update_time[topic] = now
    
    # 高亮显示重要主题
    important_topics = {
        'plugged_in': '🔌 充电枪',
        'charging_state': '⚡ 充电状态',
        'keep_accessory_power_on': '🔋 配件电源',
        'state': '🚗 车辆状态',
    }
    
    is_important = False
    display_name = topic
    
    for key, name in important_topics.items():
        if key in topic:
            is_important = True
            display_name = name
            break
    
    if is_important:
        print("=" * 80)
        print(f"⭐ {display_name}")
        print(f"   主题: {topic}")
        print(f"   值: {payload}")
        print(f"   时间: {now}")
        print("=" * 80)
        print()
    else:
        print(f"[{now}] {topic}: {payload}")


def main():
    print("\n" + "=" * 80)
    print("TeslaMate MQTT 诊断工具")
    print("=" * 80)
    print(f"MQTT Broker: {MQTT_BROKER}:{MQTT_PORT}")
    print(f"车辆 ID: {CAR_ID}")
    print("=" * 80)
    print()
    
    # 创建MQTT客户端
    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id="teslamate_diagnostic"
    )
    
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        print("正在连接到MQTT broker...")
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        
        # 启动循环
        client.loop_start()
        
        # 每30秒显示一次统计
        last_summary = time.time()
        
        while True:
            time.sleep(1)
            
            # 每30秒显示一次收到的消息统计
            if time.time() - last_summary > 30:
                print("\n" + "-" * 80)
                print(f"📊 统计 ({datetime.now().strftime('%H:%M:%S')})")
                print("-" * 80)
                print(f"已收到 {len(received_messages)} 个不同主题的消息")
                
                # 显示重要主题的当前值
                important_keys = ['plugged_in', 'keep_accessory_power_on', 'charging_state', 'state']
                print("\n关键状态:")
                for key in important_keys:
                    found = False
                    for topic, value in received_messages.items():
                        if key in topic:
                            update_time = last_update_time.get(topic, '未知')
                            print(f"  • {topic}: {value} (最后更新: {update_time})")
                            found = True
                            break
                    if not found:
                        print(f"  • {key}: ❌ 未收到")
                
                print("-" * 80)
                print("继续监听...\n")
                last_summary = time.time()
                
    except KeyboardInterrupt:
        print("\n\n收到中断信号，正在退出...")
        
        # 显示最终统计
        print("\n" + "=" * 80)
        print("📊 最终统计")
        print("=" * 80)
        print(f"总共收到 {len(received_messages)} 个不同主题的消息")
        
        if len(received_messages) == 0:
            print("\n⚠️  警告: 没有收到任何TeslaMate消息!")
            print("\n可能的原因:")
            print("  1. TeslaMate 未运行")
            print("  2. TeslaMate 未配置MQTT发布")
            print("  3. MQTT broker地址或端口配置错误")
            print("  4. 车辆ID配置错误")
            print("\n建议:")
            print("  - 检查TeslaMate是否运行: docker ps 或 systemctl status teslamate")
            print("  - 检查TeslaMate日志")
            print("  - 确认MQTT配置正确")
        else:
            print("\n关键主题:")
            important_keys = ['plugged_in', 'keep_accessory_power_on', 'charging_state', 'state']
            for key in important_keys:
                found = False
                for topic, value in received_messages.items():
                    if key in topic:
                        print(f"  ✓ {topic}: {value}")
                        found = True
                        break
                if not found:
                    print(f"  ✗ {key}: 未收到")
        
        print("=" * 80)
        
    except Exception as e:
        print(f"\n✗ 错误: {e}")
    finally:
        client.loop_stop()
        client.disconnect()
        sys.exit(0)


if __name__ == "__main__":
    main()
