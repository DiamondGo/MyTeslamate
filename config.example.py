"""
配置文件示例

使用方法：
1. 复制此文件为 config.py
2. 根据您的实际情况修改配置
"""

# MQTT服务器配置
MQTT_BROKER = "localhost"  # MQTT broker地址
MQTT_PORT = 1883            # MQTT broker端口

# TeslaMate配置
CAR_ID = 1  # 您的车辆ID，默认为1
            # 如果您有多辆车，可以在TeslaMate的MQTT主题中找到对应的ID

# 日志级别 (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL = "INFO"

