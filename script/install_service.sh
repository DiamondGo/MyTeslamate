#!/bin/bash
# 安装systemd服务

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_FILE="$SCRIPT_DIR/tesla-charging-manager.service"
SYSTEMD_DIR="/etc/systemd/system"

echo "========================================"
echo "Tesla充电管理服务安装脚本"
echo "========================================"
echo ""

# 检查服务文件是否存在
if [ ! -f "$SERVICE_FILE" ]; then
    echo "错误: 找不到服务文件 $SERVICE_FILE"
    exit 1
fi

# 复制服务文件
echo "1. 复制服务文件到 $SYSTEMD_DIR ..."
sudo cp "$SERVICE_FILE" "$SYSTEMD_DIR/"
if [ $? -ne 0 ]; then
    echo "错误: 无法复制服务文件"
    exit 1
fi
echo "   ✓ 完成"

# 重新加载systemd
echo ""
echo "2. 重新加载systemd配置..."
sudo systemctl daemon-reload
if [ $? -ne 0 ]; then
    echo "错误: 无法重新加载systemd"
    exit 1
fi
echo "   ✓ 完成"

# 启动服务
echo ""
echo "3. 启动服务..."
sudo systemctl start tesla-charging-manager
if [ $? -ne 0 ]; then
    echo "错误: 无法启动服务"
    exit 1
fi
echo "   ✓ 完成"

# 检查服务状态
echo ""
echo "4. 检查服务状态..."
sudo systemctl status tesla-charging-manager --no-pager -l
echo ""

# 询问是否设置开机自启动
read -p "是否设置开机自启动? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    sudo systemctl enable tesla-charging-manager
    echo "   ✓ 已设置开机自启动"
fi

echo ""
echo "========================================"
echo "安装完成!"
echo "========================================"
echo ""
echo "常用命令："
echo "  查看状态:   sudo systemctl status tesla-charging-manager"
echo "  停止服务:   sudo systemctl stop tesla-charging-manager"
echo "  启动服务:   sudo systemctl start tesla-charging-manager"
echo "  重启服务:   sudo systemctl restart tesla-charging-manager"
echo "  查看日志:   sudo journalctl -u tesla-charging-manager -f"
echo ""

