#!/usr/bin/env python3
"""
通过TeslaMate Web API获取当前状态
"""

import requests
import json
import sys

TESLAMATE_URL = "http://localhost:4000"
CAR_ID = 1

def get_car_state():
    """从TeslaMate API获取车辆状态"""
    try:
        # TeslaMate提供WebSocket和REST API
        # 尝试获取车辆数据
        url = f"{TESLAMATE_URL}/api/car/{CAR_ID}"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"API请求失败: HTTP {response.status_code}")
            return None
    except requests.exceptions.ConnectionError:
        print(f"无法连接到TeslaMate: {TESLAMATE_URL}")
        print("请确认TeslaMate正在运行，且端口4000可访问")
        return None
    except Exception as e:
        print(f"获取状态时出错: {e}")
        return None


def main():
    print("=" * 80)
    print("TeslaMate API 状态查询")
    print("=" * 80)
    print(f"TeslaMate URL: {TESLAMATE_URL}")
    print(f"车辆 ID: {CAR_ID}\n")
    
    state = get_car_state()
    
    if state:
        print("✅ 成功获取车辆状态\n")
        print(json.dumps(state, indent=2, ensure_ascii=False))
    else:
        print("\n❌ 无法获取车辆状态")
        print("\n替代方案:")
        print("=" * 80)
        print("由于TeslaMate可能没有直接的REST API获取实时状态，")
        print("建议使用以下方法获取当前状态：\n")
        print("1️⃣  使用MQTT retained消息（最佳方案）")
        print("   在docker-compose.yml中添加：")
        print("   - MQTT_TLS_ACCEPT_INVALID_CERTS=true")
        print("   TeslaMate会将状态以retained方式发布到MQTT\n")
        print("2️⃣  在Tesla APP中执行任何操作")
        print("   - 打开APP唤醒车辆")
        print("   - 这会触发TeslaMate更新并发送MQTT消息\n")
        print("3️⃣  插拔充电枪")
        print("   - 这会触发状态变化")
        print("   - TeslaMate会立即发送MQTT更新\n")
        print("4️⃣  访问TeslaMate Web界面")
        print(f"   - 打开浏览器访问: {TESLAMATE_URL}")
        print("   - 可以看到实时状态")
        print("=" * 80)
    
    print()


if __name__ == "__main__":
    main()
