# RC Bridge — H12 Pro 遥控器 → PC 摇杆桥接

将 Skydroid H12 Pro 遥控器的摇杆数据通过 WiFi/UDP 桥接到 PC，映射为虚拟摇杆，用于飞行模拟器（VelociDrone、Liftoff、DRL Simulator 等）。

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

**遥控器端：** 编译并安装 android-app 到 H12 Pro，打开 APP → 点 **启动广播服务**。

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
