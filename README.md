# RC Bridge — H12 Pro 遥控器 → PC 摇杆桥接

将 Skydroid H12 Pro 遥控器的摇杆数据通过 WiFi/UDP 桥接到 PC，映射为 vJoy 虚拟摇杆，用于飞行模拟器（VelociDrone、Liftoff、DRL Simulator 等）。

## 原理

```
H12 Pro 遥控器
  ├── RC Bridge APP (Android)
  │     └── RCSDK 读取 12 通道摇杆值 (1050~1950)
  │           └── UDP 广播 (端口 10001)
  │                 ↓ WiFi
  PC 接收端
  ├── rc_bridge_gui.py / RCBridge.exe
  │     ├── 接收 UDP 数据
  │     ├── 映射到 vJoy 虚拟摇杆
  │     └── 可视化显示各通道值
  └── 飞行模拟器 (VelociDrone/Liftoff/DRL)
        └── 识别为游戏手柄
```

## 通道映射

| 通道 | 名称 | 类型 | 范围 |
|------|------|------|------|
| CH1 | 横滚 Roll | 摇杆 | 1050~1500~1950 |
| CH2 | 俯仰 Pitch | 摇杆 | 1050~1500~1950 |
| CH3 | 油门 Throttle | 摇杆 | 1050~1500~1950 |
| CH4 | 方向 Yaw | 摇杆 | 1050~1500~1950 |
| CH5 | 电位器 | 旋钮 | 1050~1500~1950 |
| CH6 | 电位器 | 旋钮 | 1050~1500~1950 |
| CH7~CH10 | 开关 | 两态开关 | 1050 / 1950 |
| CH11~CH12 | 备用 | — | 1500 |

## 依赖清单

| 组件 | 依赖 | 是否需要手动装 |
|------|------|:---------:|
| `RCBridge.exe` | **vJoy 驱动** ([下载](https://sourceforge.net/projects/vjoystick/)) | ✅ 必须 |
| `rc_bridge_gui.py` | Python 3 + pyvjoy + vJoy 驱动 | ✅ 必须 |
| Android APP | Android Studio + SDK 36 | ✅ 需要编译 |
| 飞行模拟器 | VelociDrone / LiftOff / DRL Simulator | ✅ 自行购买 |

**注意**：EXE 已打包 Python 和 pyvjoy，但 **vJoy 驱动仍需要手动安装**（因为 pyvjoy 调用的是系统级的 vJoyInterface.dll）。

---

## 快速开始

### 1. 安装依赖

**遥控器端**：编译并安装 android-app 到 H12 Pro（需要 Android Studio）

**PC 端**：
```bash
# 1. 安装 vJoy 驱动
# 下载: https://sourceforge.net/projects/vjoystick/
# 安装后打开 Configure vJoy:
#   - Device 1 → 4 Axes → 勾选 X Y Z Rx → Apply

# 2. 运行接收端（二选一）
# 选项 A: 直接运行 Python 脚本
pip install pyvjoy
python pc-receiver/rc_bridge_gui.py

# 选项 B: 运行打包好的 EXE（不需要 Python）
pc-receiver/dist/RCBridge.exe
```

### 2. 启动桥接

1. H12 Pro 连接电脑 WiFi（同一网段）
2. 打开 RC Bridge APP → 点 **启动广播服务**
3. PC 接收端显示通道数据
4. 打开飞行模拟器，选择 vJoy Device 作为控制器

## 项目结构

```
rc-bridge/
├── android-app/                # Android APP (Gradle)
│   ├── app/
│   │   ├── src/main/java/      # Java 源码
│   │   ├── libs/               # RCSDK AAR
│   │   └── build.gradle
│   └── build.gradle
├── pc-receiver/                # PC 接收端
│   ├── rc_bridge_gui.py        # GUI 版 (tkinter)
│   ├── requirements.txt        # Python 依赖
│   └── dist/
│       └── RCBridge.exe        # 打包好的可执行文件
├── README.md
└── .gitignore
```

## 技术细节

- **RCSDK v1.9.1** — 云卓官方 SDK，通过串口读取遥控器摇杆值
- **H12 Pro 通道读取** — GET 方式，每 50ms 主动请求一次通道值
- **UDP 广播** — 端口 10001，50Hz 发送 JSON 格式数据
- **vJoy** — 开源虚拟摇柄驱动，Python 通过 pyvjoy 控制

## 从源码构建

### Android APP

```bash
# 需要: Android Studio + SDK (API 36)
# RCSDK AAR 已包含在 app/libs/ 中

cd android-app
./gradlew assembleDebug
# APK: app/build/outputs/apk/debug/app-debug.apk
```

### PC EXE

```bash
pip install pyinstaller pyvjoy
cd pc-receiver
pyinstaller --onefile --windowed --name "RCBridge" rc_bridge_gui.py
# EXE: dist/RCBridge.exe
```

## License

MIT
