# RC Bridge — RC Remote → PC Joystick Bridge

将遥控器的摇杆数据通过 WiFi/UDP 桥接到 PC，映射为虚拟摇杆，用于飞行模拟器（VelociDrone、Liftoff、DRL Simulator 等）。

## 兼容性说明

本项目分两部分，兼容性不同：

| 组件 | 兼容情况 | 说明 |
|------|---------|------|
| **PC 接收端** （`pc-receiver/` + `pc-receiver-vigem/`） | ✅ **完全通用** | 不挑遥控器，任何设备只要往 UDP 10001 发标准 JSON 都能驱动 |
| **Android APP** （`android-app/`） | ⚠️ **仅限 Skydroid 遥控器** | 使用云卓官方 RCSDK，适合 H12 Pro / H16 / H20 等型号 |

**PC 接收端是通用模块**，不管用什么遥控器（FrSky、RadioMaster、甚至手机发 UDP 模拟数据），只要数据格式对得上就能用。换遥控器只需要改发送端，PC 端一根不用动。

## 原理

```
H12 Pro 遥控器
  ├── RC Bridge APP (Android)
  │     └── RCSDK 读取 12 通道摇杆值 (1050~1950)
  │           └── UDP 广播 (端口 10001)
  │                 ↓ WiFi
  PC 接收端
  ├── [vJoy 版] rc_bridge_gui.py / RCBridge.exe
  │     └── vJoy 虚拟摇杆 → 飞行模拟器
  └── [ViGEmBus 版] rc_bridge_vigem.py (推荐)
        └── 虚拟 Xbox 360 手柄 → 飞行模拟器
```

## 两版对比

| | vJoy 版 | ViGEmBus 版 ⭐ |
|--|:-------:|:-------------:|
| 驱动 | vJoy (需手动配置轴) | ViGEmBus (即装即用) |
| 卡死问题 | 偶尔 BUSY 卡死 | ✅ 永不卡死 |
| 游戏识别 | 部分游戏不认 | ✅ 所有游戏认 Xbox 手柄 |
| 轴配置 | 需手动设置 4 Axes | ✅ 即开即用 |
| 成功率 | ~60% | **~95%** |

**推荐使用 ViGEmBus 版**，兼容性更好，不需要任何配置。

## 通道映射 (Mode 2 美国手)

| 通道 | 名称 | 摇杆方向 | 范围 |
|------|------|---------|------|
| CH1 | 横滚 Roll | 右摇杆 ←→ | 1050~1500~1950 |
| CH2 | 俯仰 Pitch | 右摇杆 ↑↓ | 1050~1500~1950 |
| CH3 | 油门 Throttle | 左摇杆 ↑↓ | 1050~1500~1950 |
| CH4 | 方向 Yaw | 左摇杆 ←→ | 1050~1500~1950 |
| CH5 | 电位器 | 旋钮 | 1050~1500~1950 |
| CH6 | 电位器 | 旋钮 | 1050~1500~1950 |
| CH7~CH10 | 开关 (→ Xbox A/B/X/Y) | 两态开关 | 1050 / 1950 |
| CH11~CH12 | 备用 | — | 1500 |

## 快速开始

### ViGEmBus 版（推荐）

**PC 端：**
```bash
# 1. 安装 ViGEmBus 驱动
# 下载: https://github.com/nefarius/ViGEmBus/releases
# 安装后重启电脑

# 2. 安装 Python 依赖
pip install vgamepad

# 3. 运行接收端
cd pc-receiver-vigem
python rc_bridge_vigem.py
```

**遥控器端（仅限 Skydroid 遥控器）：** 编译并安装 android-app 到 H12 Pro（或其他云卓遥控器），打开 APP → 点 **启动广播服务**。

其他品牌遥控器需要自行实现发送端，往 UDP 10001 发送 JSON：

```json
{"ch1":1500,"ch2":1500,"ch3":1500,"ch4":1500,"ch5":1050,"ch6":1500,"ch7":1950,"ch8":1050,"ch9":1050,"ch10":1950,"ts":1700000000000}
```

字段说明：`ch1`~`ch12` 为各通道值（范围 1050~1950），`ts` 为毫秒时间戳。PC 端只认这个格式，不管是谁发的。

### vJoy 版

**PC 端：**
```bash
# 1. 安装 vJoy 驱动
# 下载: https://sourceforge.net/projects/vjoystick/
# 安装后打开 Configure vJoy:
#   - Number of Axes → 4 → 勾选 X Y Z Rx → Apply

# 2. 运行接收端（二选一）
# 选项 A: Python 脚本
pip install pyvjoy
python pc-receiver/rc_bridge_gui.py

# 选项 B: 打包好的 EXE
pc-receiver/dist/RCBridge.exe
```

## 项目结构

```
rc-bridge/
├── android-app/                    # Android APP (Gradle)
│   ├── app/
│   │   ├── src/main/java/          # Java 源码
│   │   ├── libs/                   # RCSDK AAR
│   │   └── build.gradle
│   └── build.gradle
├── pc-receiver/                    # PC 接收端 - vJoy 版
│   ├── rc_bridge_gui.py            # GUI 版 (tkinter)
│   ├── rc_receiver.py              # 核心接收逻辑
│   ├── requirements.txt            # Python 依赖
│   └── dist/
│       └── RCBridge.exe            # 打包好的可执行文件
├── pc-receiver-vigem/              # PC 接收端 - ViGEmBus 版 ⭐
│   ├── rc_bridge_vigem.py          # 虚拟 Xbox 360 手柄
│   └── requirements.txt            # vgamepad 依赖
├── README.md
└── .gitignore
```

## 技术细节

- **RCSDK v1.9.1** — 云卓官方 SDK，通过串口读取遥控器摇杆值
- **H12 Pro 通道读取** — GET 方式，每 50ms 主动请求一次通道值
- **UDP 广播** — 端口 10001，50Hz 发送 JSON 格式数据
- **vJoy** — 开源虚拟摇杆驱动，Python 通过 pyvjoy 控制
- **ViGEmBus** — 虚拟总线驱动，通过 vgamepad 模拟 Xbox 360 手柄
  - CH7~CH10 开关映射为 A/B/X/Y 按键
  - CH3 油门同时映射到左扳机，便于更精细控制

## 从源码构建

### Android APP

```bash
# 需要: Android Studio + SDK (API 36)
# RCSDK AAR 已包含在 app/libs/ 中

cd android-app
./gradlew assembleDebug
# APK: app/build/outputs/apk/debug/app-debug.apk
```

### PC EXE (vJoy 版)

```bash
pip install pyinstaller pyvjoy
cd pc-receiver
pyinstaller --onefile --windowed --name "RCBridge" rc_bridge_gui.py
# EXE: dist/RCBridge.exe
```

## License

MIT
