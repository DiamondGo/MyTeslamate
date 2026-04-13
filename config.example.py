"""
配置文件示例

使用方法：
1. 复制此文件为 config.py
2. 根据您的实际情况修改配置
"""

# MQTT服务器配置
MQTT_BROKER = "localhost"   # MQTT broker 地址（mosquitto 容器所在主机）
MQTT_PORT = 1883            # MQTT broker 端口

# TeslaMate Web 地址
TESLAMATE_URL = "http://localhost:4000"

# TeslaMate配置
CAR_ID = 1          # 您的车辆ID，默认为1
                    # 如果您有多辆车，可以在TeslaMate的MQTT主题中找到对应的ID
MQTT_NAMESPACE = "teslamate"  # docker-compose.yml 中 MQTT_NAMESPACE 的值

# 日志级别 (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL = "INFO"
