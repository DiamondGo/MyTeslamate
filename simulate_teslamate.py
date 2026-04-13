#!/usr/bin/env python3
"""
模拟TeslaMate发送MQTT消息的测试脚本

用于测试charging_accessory_manager.py的功能
"""

import paho.mqtt.client as mqtt
import time
import sys

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
CAR_ID = 1

# MQTT主题
TOPIC_PLUGGED_IN = f"teslamate/cars/{CAR_ID}/plugged_in"
TOPIC_ACCESSORY_POWER = f"teslamate/cars/{CAR_ID}/keep_accessory_power_on"

def publish_state(client, plugged_in, accessory_power):
    """发布状态"""
    print(f"\n发布状态:")
    print(f"  充电枪: {'已插入' if plugged_in else '未插入'}")
    print(f"  配件电源: {'ON' if accessory_power else 'OFF'}")
    
    client.publish(TOPIC_PLUGGED_IN, "true" if plugged_in else "false", retain=True)
    client.publish(TOPIC_ACCESSORY_POWER, "true" if accessory_power else "false", retain=True)
    time.sleep(0.5)

def main():
    print("=" * 60)
    print("TeslaMate MQTT 模拟器")
    print("=" * 60)
    print(f"MQTT Broker: {MQTT_BROKER}:{MQTT_PORT}")
    print(f"车辆ID: {CAR_ID}")
    print("=" * 60)
    
    # 创建MQTT客户端
    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id="teslamate_simulator"
    )
    
    try:
        print("正在连接到MQTT broker...")
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        client.loop_start()
        print("✓ 已连接\n")
        
        while True:
            print("\n" + "=" * 60)
            print("选择操作:")
            print("1. 设置初始状态 (未插入, 配件电源OFF)")
            print("2. 设置初始状态 (未插入, 配件电源ON)")
            print("3. 插入充电枪")
            print("4. 拔出充电枪")
            print("5. 切换配件电源状态")
            print("6. 运行完整测试场景")
            print("0. 退出")
            print("=" * 60)
            
            choice = input("请选择 (0-6): ").strip()
            
            if choice == "1":
                publish_state(client, False, False)
            elif choice == "2":
                publish_state(client, False, True)
            elif choice == "3":
                publish_state(client, True, client._userdata.get('accessory', False))
            elif choice == "4":
                publish_state(client, False, client._userdata.get('accessory', False))
            elif choice == "5":
                current = client._userdata.get('accessory', False)
                publish_state(client, client._userdata.get('plugged', False), not current)
                client._userdata['accessory'] = not current
            elif choice == "6":
                print("\n开始完整测试场景...")
                print("\n1️⃣ 初始状态：未插入，配件电源OFF")
                publish_state(client, False, False)
                time.sleep(2)
                
                print("\n2️⃣ 插入充电枪")
                publish_state(client, True, False)
                time.sleep(2)
                
                print("\n3️⃣ (模拟脚本将配件电源设为ON)")
                time.sleep(1)
                publish_state(client, True, True)
                time.sleep(2)
                
                print("\n4️⃣ 拔出充电枪")
                publish_state(client, False, True)
                time.sleep(2)
                
                print("\n5️⃣ (模拟脚本恢复配件电源为OFF)")
                time.sleep(1)
                publish_state(client, False, False)
                
                print("\n✅ 测试场景完成!")
            elif choice == "0":
                print("\n退出...")
                break
            else:
                print("\n无效选择，请重试")
                
    except KeyboardInterrupt:
        print("\n\n收到中断信号，正在退出...")
    except Exception as e:
        print(f"\n错误: {e}")
    finally:
        client.loop_stop()
        client.disconnect()
        sys.exit(0)

if __name__ == "__main__":
    if not hasattr(mqtt.Client, '_userdata'):
        mqtt.Client._userdata = {}
    main()
