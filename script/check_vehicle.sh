#!/bin/bash
# 快速查看车辆状态

cd "$(dirname "$0")"
./venv/bin/python3 get_mqtt_status.py
