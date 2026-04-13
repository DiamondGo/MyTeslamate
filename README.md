# Tesla 充电配件电源自动管理

这个脚本用于自动管理Tesla车辆在充电时的"Keep Accessory Power On"设置。

## 功能

- **插入充电枪时**：自动记录当前的"Keep Accessory Power On"状态，并将其设置为ON
- **拔出充电枪时**：自动恢复到插入充电枪之前的状态

## 前置要求

- TeslaMate 已安装并正常运行
- MQTT broker (通常是Mosquitto) 运行在端口 1883
- Python 3.12+
- paho-mqtt 库

## 安装步骤

### 1. 确认依赖已安装

```bash
# 进入项目目录
cd /home/ken/source/teslaAutomate

# 激活虚拟环境
source venv/bin/activate

# 确认paho-mqtt已安装
pip list | grep paho-mqtt
```

### 2. 配置脚本

编辑 `charging_accessory_manager.py` 文件，修改以下配置（如果需要）：

```python
MQTT_BROKER = "localhost"  # MQTT服务器地址
MQTT_PORT = 1883           # MQTT端口
CAR_ID = 1                 # 车辆ID（在TeslaMate中的ID）
```

### 3. 测试运行

```bash
# 在虚拟环境中运行
source venv/bin/activate
python3 charging_accessory_manager.py
```

您应该看到类似以下的输出：
```
2024-XX-XX XX:XX:XX - INFO - ============================================================
2024-XX-XX XX:XX:XX - INFO - Tesla充电配件电源管理脚本启动
2024-XX-XX XX:XX:XX - INFO - MQTT Broker: localhost:1883
2024-XX-XX XX:XX:XX - INFO - 车辆ID: 1
2024-XX-XX XX:XX:XX - INFO - ============================================================
2024-XX-XX XX:XX:XX - INFO - 正在连接到MQTT broker...
2024-XX-XX XX:XX:XX - INFO - 成功连接到MQTT broker: localhost:1883
2024-XX-XX XX:XX:XX - INFO - 已订阅主题: teslamate/cars/1/plugged_in
2024-XX-XX XX:XX:XX - INFO - 已订阅主题: teslamate/cars/1/keep_accessory_power_on
```

### 4. 设置为系统服务（开机自启动）

```bash
# 复制服务文件到systemd目录
sudo cp tesla-charging-manager.service /etc/systemd/system/

# 重新加载systemd配置
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start tesla-charging-manager

# 查看服务状态
sudo systemctl status tesla-charging-manager

# 设置开机自启动
sudo systemctl enable tesla-charging-manager
```

### 5. 查看日志

```bash
# 查看实时日志
sudo journalctl -u tesla-charging-manager -f

# 查看最近的日志
sudo journalctl -u tesla-charging-manager -n 50
```

## TeslaMate MQTT 主题说明

脚本使用以下MQTT主题：

- **订阅**：
  - `teslamate/cars/{CAR_ID}/plugged_in` - 充电枪插入状态（true/false）
  - `teslamate/cars/{CAR_ID}/keep_accessory_power_on` - 配件电源状态（true/false）

- **发布**：
  - `teslamate/cars/{CAR_ID}/command/keep_accessory_power_on` - 控制配件电源（on/off）

## 工作原理

1. 脚本持续监听TeslaMate发布的充电枪插拔状态
2. 当检测到充电枪插入（`plugged_in` 变为 `true`）：
   - 记录当前的 `keep_accessory_power_on` 状态
   - 如果当前不是ON，则发送命令将其设置为ON
3. 当检测到充电枪拔出（`plugged_in` 变为 `false`）：
   - 恢复之前记录的 `keep_accessory_power_on` 状态

## 故障排除

### 脚本无法连接到MQTT

检查MQTT服务是否运行：
```bash
sudo systemctl status mosquitto
```

检查端口是否开放：
```bash
netstat -an | grep 1883
```

### 找不到车辆ID

查看TeslaMate的MQTT主题来确定车辆ID：
```bash
mosquitto_sub -h localhost -t "teslamate/cars/#" -v
```

### 查看详细调试信息

修改脚本中的日志级别：
```python
logging.basicConfig(
    level=logging.DEBUG,  # 改为DEBUG
    format='%(asctime)s - %(levelname)s - %(message)s'
)
```

## 停止服务

```bash
# 停止服务
sudo systemctl stop tesla-charging-manager

# 禁用开机自启动
sudo systemctl disable tesla-charging-manager
```

## 许可证

MIT License

