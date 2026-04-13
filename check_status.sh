#!/bin/bash
# 检查Tesla充电管理服务和MQTT状态

echo "========================================"
echo "Tesla充电管理 - 状态检查"
echo "========================================"
echo ""

# 检查MQTT服务
echo "1. MQTT服务状态:"
if systemctl is-active --quiet mosquitto; then
    echo "   ✓ Mosquitto MQTT 运行中"
else
    echo "   ✗ Mosquitto MQTT 未运行"
    echo "   尝试启动: sudo systemctl start mosquitto"
fi
echo ""

# 检查MQTT端口
echo "2. MQTT端口检查:"
if netstat -an 2>/dev/null | grep -q ":1883.*LISTEN" || ss -an 2>/dev/null | grep -q ":1883.*LISTEN"; then
    echo "   ✓ 端口 1883 正在监听"
else
    echo "   ✗ 端口 1883 未开放"
fi
echo ""

# 检查Tesla充电管理服务
echo "3. Tesla充电管理服务:"
if systemctl list-unit-files | grep -q tesla-charging-manager; then
    if systemctl is-active --quiet tesla-charging-manager; then
        echo "   ✓ 服务运行中"
        if systemctl is-enabled --quiet tesla-charging-manager; then
            echo "   ✓ 已设置开机自启动"
        else
            echo "   ⚠ 未设置开机自启动"
            echo "   设置自启动: sudo systemctl enable tesla-charging-manager"
        fi
    else
        echo "   ✗ 服务未运行"
        echo "   启动服务: sudo systemctl start tesla-charging-manager"
    fi
else
    echo "   ⚠ 服务未安装"
    echo "   安装服务: ./install_service.sh"
fi
echo ""

# 检查TeslaMate MQTT消息
echo "4. TeslaMate MQTT消息检查:"
echo "   正在监听TeslaMate消息 (3秒)..."
timeout 3 mosquitto_sub -h localhost -t "teslamate/cars/#" -C 1 2>/dev/null
if [ $? -eq 0 ]; then
    echo "   ✓ 接收到TeslaMate消息"
else
    echo "   ✗ 未接收到TeslaMate消息"
    echo "   请检查TeslaMate是否正在运行"
fi
echo ""

# 显示最近的日志
if systemctl list-unit-files | grep -q tesla-charging-manager; then
    if systemctl is-active --quiet tesla-charging-manager; then
        echo "5. 最近的日志 (最后10行):"
        echo "----------------------------------------"
        sudo journalctl -u tesla-charging-manager -n 10 --no-pager
        echo "----------------------------------------"
        echo ""
    fi
fi

echo "========================================"
echo "检查完成"
echo "========================================"
echo ""
echo "常用命令："
echo "  查看详细状态:  sudo systemctl status tesla-charging-manager"
echo "  查看实时日志:  sudo journalctl -u tesla-charging-manager -f"
echo "  测试MQTT:      ./test.sh"
echo ""

