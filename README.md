# RC Bridge 遥控器桥接

[![version](https://img.shields.io/badge/version-v0.1-blue)]()
[![platform](https://img.shields.io/badge/platform-Windows%20%7C%20Android-blue)]()
[![license](https://img.shields.io/badge/license-MIT-green)]()

> 用 Skydroid H12 Pro 遥控器飞 PC 模拟器。摇杆 → WiFi → 虚拟 Xbox 手柄，即开即飞。

---

## ⬇️ 下载

<div align="center">

| 文件 | 大小 | 用途 |
|------|------|------|
| 📱 [rc-bridge-v0.1-android.apk](./dist/rc-bridge-v0.1-android.apk) | 8.4 MB | **装到遥控器上**，安装后点"启动广播" |
| 🎮 [rc-bridge-v0.1-vigem.exe](./dist/rc-bridge-v0.1-vigem.exe) | 9.3 MB | **在 PC 上双击**，自动变虚拟手柄 |
| 🚀 [start.bat](./start.bat) | — | 一键启动（检测驱动 + 启动桥接） |

</div>

---

## 🚀 三步上手

| # | 步骤 | 需要时间 |
|---|------|---------|
| **1** | PC 装 [ViGEmBus 驱动](https://github.com/nefarius/ViGEmBus/releases)（首次，只需一次） | 1 分钟 |
| **2** | 双击 `rc-bridge-v0.1-vigem.exe`，遥控器上打开 APP 点 **「启动广播」** | 10 秒 |
| **3** | 打开飞行模拟器，开飞 ✈️ | — |

> 💡 以后每次飞只需要 **第 2 步**，驱动装一次就行。

---

## 🧩 兼容性

| 组件 | 兼容情况 |
|------|---------|
| PC 接收端 | ✅ **完全不挑遥控器**，任何设备，UDP 发 JSON 就行 |
| Android APP（遥控器端） | ⚠️ **仅限 Skydroid 遥控器**（H12 Pro / H16 / H20 等） |

PC 端是通用模块 —— 换个遥控器只需要改发送端，PC 端不动。

---

## 🌐 网络要求

**遥控器和 PC 必须在同一局域网内。**

| 方式 | 说明 |
|------|------|
| **路由器** | H12 Pro 连接 WiFi 路由器，PC 也连同一个路由器（有线/无线均可） |
| **PC 开热点** | 在 Windows 设置中开启「移动热点」，H12 Pro 连接该热点 |
| **手机热点** | 手机开热点，H12 Pro 和 PC 都连这个热点 |

> ⚠️ 遥控器通过 UDP 广播（端口 10001）发送数据，不需要电脑的 IP 地址，但双方必须在同一个子网。
>
> 如果连接不上，先在遥控器上检查 WiFi 图标是否亮起，再确认 PC 防火墙没有拦截 UDP 10001 端口。

---

## 🔧 原理

```
H12 Pro 遥控器
  └── RC Bridge APP (Android)
        └── RCSDK 读取 12 通道 (1050~1950)
              └── UDP 广播 (端口 10001)
                    ↓ WiFi
PC 接收端
  ├── ⭐ ViGEmBus 版  →  虚拟 Xbox 360 手柄  →  模拟器
  └── vJoy 版         →  vJoy 虚拟摇杆        →  模拟器
```

---

## 🕹️ 通道映射 (Mode 2 美国手)

| 通道 | 功能 | 摇杆 | 范围 |
|------|------|------|------|
| CH1 | 横滚 Roll | 右摇杆 ←→ | 1050 ← 1500 → 1950 |
| CH2 | 俯仰 Pitch | 右摇杆 ↑↓ | 1050 ← 1500 → 1950 |
| CH3 | 油门 Throttle | 左摇杆 ↑↓ | 1050 ← 1500 → 1950 |
| CH4 | 方向 Yaw | 左摇杆 ←→ | 1050 ← 1500 → 1950 |
| CH5~CH6 | 电位器（旋钮） | — | 1050 ← 1500 → 1950 |
| CH7~CH10 | 开关 → Xbox A/B/X/Y | 两态 | 1050 / 1950 |
| CH11~CH12 | 备用 | — | 1500 |

---

## ⚖️ 版本对比

| | vJoy 版 | **ViGEmBus 版** ⭐ |
|--|:-------:|:-----------------:|
| 驱动 | 需手动配轴 | 即装即用 |
| 卡死 | 偶尔 BUSY 卡死 | ✅ 永不 |
| 游戏识别 | 部分不认 | ✅ 所有游戏 |
| 配置 | 手动设 4 Axes | ✅ 零配置 |
| 成功率 | ~60% | **~95%** |

**推荐 ViGEmBus 版**，好用得多。

---

## 📋 详细安装

### ViGEmBus 版（推荐）

**PC 端（二选一）：**

**A. 双击 exe（推荐）**
```
dist\rc-bridge-v0.1-vigem.exe
```

**B. Python 运行**
```bash
pip install vgamepad
cd pc-receiver-vigem
python rc_bridge_vigem.py
```

**遥控器端：** 装 `dist/rc-bridge-v0.1-android.apk` → 打开 APP → **启动广播服务**

> 其他遥控器：往 UDP 10001 发 JSON 就行
> ```json
> {"ch1":1500,"ch2":1500,"ch3":1500,"ch4":1500,"ch5":1050,"ch6":1500,"ch7":1950,"ch8":1050,"ch9":1050,"ch10":1950,"ts":1700000000000}
> ```
> `ch1~ch12` 范围 1050~1950，`ts` 是毫秒时间戳。

### vJoy 版

```bash
# 1. 装 vJoy 驱动
#    https://sourceforge.net/projects/vjoystick/
#    装完打开 Configure vJoy → Number of Axes=4 → 勾 X Y Z Rx → Apply

# 2. 运行
pip install pyvjoy
python pc-receiver/rc_bridge_gui.py
```

---

## 📁 项目结构

```
rc-bridge/
├── android-app/                   # 遥控器 APP 源码
├── pc-receiver/                   # PC 接收端 - vJoy 版
├── pc-receiver-vigem/             # PC 接收端 - ViGEmBus 版 ⭐
├── dist/                          # 预编译下载
│   ├── rc-bridge-v0.1-android.apk
│   └── rc-bridge-v0.1-vigem.exe
├── start.bat                      # 一键启动
├── README.md
└── .gitignore
```

---

## 🔨 从源码构建

### Android APP
```bash
# 需要: Android Studio + SDK (API 36)
cd android-app
./gradlew assembleDebug
# APK → app/build/outputs/apk/debug/app-debug.apk
```

### PC EXE (ViGEmBus 版)
```bash
pip install pyinstaller
cd pc-receiver-vigem
pyinstaller --onefile --name "rc-bridge-vigem" --collect-all vgamepad --console rc_bridge_vigem.py
```

### PC EXE (vJoy 版)
```bash
pip install pyinstaller pyvjoy
cd pc-receiver
pyinstaller --onefile --windowed --name "RCBridge" rc_bridge_gui.py
```

---

## ⚙️ 技术细节

- **RCSDK v1.9.1** — 云卓官方 SDK，串口读取摇杆
- **H12 Pro** — GET 模式，每 50ms 请求一次通道值
- **UDP 端口 10001** — 数据驱动广播，poll 回调拿到数据即发，无额外延迟
- **死区 DEADZONE=20** — 摇杆回中偏 20 以内视为中位，防漂移
- **ViGEmBus** — 模拟 Xbox 360 手柄，CH7~CH10 映射 A/B/X/Y 按键

---

## 📄 License

**本项目代码** © 2026 李阳，基于 MIT License 开源 —— 详见 [LICENSE](./LICENSE)。

**第三方组件：**
| 组件 | License |
|------|---------|
| RCSDK v1.9.1 (android-app/libs/) | ⚠️ **Skydroid 专有许可** — 闭源二进制，仅限搭配云卓遥控器使用 |
| ViGEmBus (驱动) | BSD 3-Clause |
| vgamepad (Python 库) | MIT |
| vJoy (驱动) | BSD 3-Clause |

详见 [NOTICE](./NOTICE)。
