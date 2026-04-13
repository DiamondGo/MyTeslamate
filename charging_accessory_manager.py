#!/usr/bin/env python3
"""
TeslaMate充电配件电源管理脚本

功能：
- 当Tesla插上充电枪时，记录"keep accessory power on"的当前值，并将其设置为on
- 当拔下充电枪时，恢复之前记录的值
"""

import paho.mqtt.client as mqtt
import json
import logging
import sys
import time
import threading

# 配置
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
CAR_ID = 1  # TeslaMate中的车辆ID，默认为1，如果有多辆车请修改

# MQTT主题
TOPIC_PLUGGED_IN = f"teslamate/cars/{CAR_ID}/plugged_in"
TOPIC_ACCESSORY_POWER = f"teslamate/cars/{CAR_ID}/keep_accessory_power_on"
TOPIC_COMMAND = f"teslamate/cars/{CAR_ID}/command/keep_accessory_power_on"

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 全局状态
class State:
    def __init__(self):
        self.plugged_in = None
        self.accessory_power_original = None
        self.accessory_power_current = None
        self.initial_state_received = threading.Event()
        self.received_plugged_in = False
        self.received_accessory_power = False

    def check_initial_state_complete(self):
        """检查是否已接收到初始状态"""
        if self.received_plugged_in and self.received_accessory_power:
            self.initial_state_received.set()

state = State()


def on_connect(client, userdata, flags, reason_code, properties):
    """MQTT连接回调"""
    if reason_code == 0:
        logger.info(f"成功连接到MQTT broker: {MQTT_BROKER}:{MQTT_PORT}")
        # 订阅充电状态和配件电源状态主题
        # QoS=0, 但如果消息是retained的，会立即收到
        client.subscribe(TOPIC_PLUGGED_IN, qos=0)
        client.subscribe(TOPIC_ACCESSORY_POWER, qos=0)
        logger.info(f"已订阅主题: {TOPIC_PLUGGED_IN}")
        logger.info(f"已订阅主题: {TOPIC_ACCESSORY_POWER}")
        logger.info("正在获取当前状态...")
        logger.info("提示: 如果TeslaMate设置了MQTT retained消息，会立即显示当前状态")
        logger.info("     否则需要等待车辆状态发生变化")
    else:
        logger.error(f"连接失败，错误码: {reason_code}")


def on_message(client, userdata, msg):
    """MQTT消息回调"""
    topic = msg.topic
    payload = msg.payload.decode('utf-8')
    
    logger.debug(f"收到消息 - 主题: {topic}, 内容: {payload}")
    
    if topic == TOPIC_PLUGGED_IN:
        handle_plugged_in_change(client, payload)
    elif topic == TOPIC_ACCESSORY_POWER:
        handle_accessory_power_status(client, payload)


def handle_plugged_in_change(client, payload):
    """处理充电枪插拔状态变化"""
    try:
        # TeslaMate发布的是 "true" 或 "false" 字符串
        is_plugged_in = payload.lower() == "true"

        # 首次接收状态
        if not state.received_plugged_in:
            state.received_plugged_in = True
            state.plugged_in = is_plugged_in
            logger.info(f"📍 当前充电枪状态: {'已插入 ✓' if is_plugged_in else '未插入 ✗'}")
            state.check_initial_state_complete()
            return

        # 如果状态没有变化，忽略
        if state.plugged_in == is_plugged_in:
            return

        logger.info(f"🔄 充电枪状态变化: {'已插入 ✓' if is_plugged_in else '已拔出 ✗'}")
        state.plugged_in = is_plugged_in
        
        if is_plugged_in:
            # 插入充电枪：记录当前值并设置为on
            logger.info(f"检测到充电枪插入，当前配件电源状态: {state.accessory_power_current}")
            if state.accessory_power_current is not None:
                state.accessory_power_original = state.accessory_power_current
                logger.info(f"已记录原始配件电源状态: {state.accessory_power_original}")
                
                # 如果当前不是on，则设置为on
                if state.accessory_power_current != "true":
                    logger.info("设置配件电源为ON")
                    client.publish(TOPIC_COMMAND, "on", qos=1)
                else:
                    logger.info("配件电源已经是ON，无需更改")
            else:
                logger.warning("配件电源当前状态未知，等待状态更新")
        else:
            # 拔出充电枪：恢复原始值
            if state.accessory_power_original is not None:
                logger.info(f"检测到充电枪拔出，恢复配件电源状态为: {state.accessory_power_original}")
                command = "on" if state.accessory_power_original == "true" else "off"
                client.publish(TOPIC_COMMAND, command, qos=1)
                state.accessory_power_original = None
            else:
                logger.info("没有记录的原始配件电源状态，不进行恢复")
                
    except Exception as e:
        logger.error(f"处理充电状态变化时出错: {e}")


def handle_accessory_power_status(client, payload):
    """处理配件电源状态更新"""
    try:
        new_value = payload.lower()

        # 首次接收状态
        if not state.received_accessory_power:
            state.received_accessory_power = True
            state.accessory_power_current = new_value
            logger.info(f"🔋 当前配件电源状态: {'ON ✓' if new_value == 'true' else 'OFF ✗'}")
            state.check_initial_state_complete()
            return

        # 检查状态是否变化
        if state.accessory_power_current != new_value:
            old_value = state.accessory_power_current
            state.accessory_power_current = new_value
            logger.info(f"🔄 配件电源状态变化: {'OFF' if old_value == 'true' else 'ON'} → {'ON ✓' if new_value == 'true' else 'OFF ✗'}")
        else:
            state.accessory_power_current = new_value
            logger.debug(f"配件电源状态更新: {state.accessory_power_current}")
    except Exception as e:
        logger.error(f"处理配件电源状态时出错: {e}")


def on_disconnect(client, userdata, reason_code, properties):
    """MQTT断开连接回调"""
    logger.warning(f"与MQTT broker断开连接，原因码: {reason_code}")


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("Tesla充电配件电源管理脚本启动")
    logger.info(f"MQTT Broker: {MQTT_BROKER}:{MQTT_PORT}")
    logger.info(f"车辆ID: {CAR_ID}")
    logger.info("=" * 60)

    # 创建MQTT客户端
    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id="tesla_charging_accessory_manager"
    )

    # 设置回调函数
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect

    # 连接到MQTT broker
    try:
        logger.info(f"正在连接到MQTT broker...")
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    except Exception as e:
        logger.error(f"连接失败: {e}")
        sys.exit(1)

    # 在后台启动MQTT循环
    client.loop_start()

    # 等待接收初始状态（最多5秒）
    logger.info("等待接收初始状态...")
    if state.initial_state_received.wait(timeout=5):
        logger.info("-" * 60)
        logger.info("✅ 初始状态已获取，开始监控状态变化")
        logger.info("-" * 60)
    else:
        logger.info("-" * 60)
        logger.info("ℹ️  未能立即获取状态（TeslaMate可能在车辆活动时才发送更新）")
        logger.info("脚本将继续运行，当状态更新时会自动显示")
        logger.info("-" * 60)

    # 保持运行
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在退出...")
        client.loop_stop()
        client.disconnect()
        sys.exit(0)


if __name__ == "__main__":
    main()

