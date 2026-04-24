#!/bin/bash
# 启动Tesla充电配件电源管理脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "启动Tesla充电配件电源管理脚本..."
echo "按 Ctrl+C 停止"
echo ""

# 激活虚拟环境并运行脚本
source venv/bin/activate
python3 charging_accessory_manager.py

