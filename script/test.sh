#!/bin/bash
# 测试MQTT主题

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "启动MQTT主题测试工具..."
echo "按 Ctrl+C 停止"
echo ""

# 激活虚拟环境并运行测试脚本
source venv/bin/activate
python3 test_mqtt_topics.py

