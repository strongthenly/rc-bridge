"""
RC Bridge - PC 接收端 (GUI 版)
可视化显示摇杆数据，自动映射到 vJoy
"""
import tkinter as tk
from tkinter import ttk
import threading
import json
import socket
import time
import ctypes
import os
import sys

# ============================================================
# vJoy 初始化
# ============================================================
def init_vjoy():
    dll_path = r"C:\Program Files\vJoy\x64\vJoyInterface.dll"
    if os.path.exists(dll_path):
        dll = ctypes.CDLL(dll_path)
        dll.RelinquishVJD(1)
        dll.GetVJDStatus.restype = ctypes.c_uint
        dll.AcquireVJD.restype = ctypes.c_bool
        for _ in range(5):
            st = dll.GetVJDStatus(1)
            if st == 1:
                break
            dll.RelinquishVJD(1)
            time.sleep(0.5)

    import pyvjoy
    global vjoy_dev, AXIS_MAP
    vjoy_dev = pyvjoy.VJoyDevice(1)
    AXIS_MAP = {
        1: pyvjoy.HID_USAGE_X, 2: pyvjoy.HID_USAGE_Y,
        3: pyvjoy.HID_USAGE_Z, 4: pyvjoy.HID_USAGE_RX,
        5: pyvjoy.HID_USAGE_RY, 6: pyvjoy.HID_USAGE_RZ,
        7: pyvjoy.HID_USAGE_SL0, 8: pyvjoy.HID_USAGE_SL1,
    }  # H12 Pro: CH1-4 sticks, CH5-6 pots, CH7-10 switches, CH11-12 unused
    return True

vjoy_dev = None
AXIS_MAP = {}
CHANNEL_NAMES = ["横滚 Roll", "俯仰 Pitch", "油门 Throttle", "方向 Yaw",
                 "CH5 电位", "CH6 电位", "CH7 开关", "CH8 开关",
                 "CH9 开关", "CH10 开关", "CH11 备用", "CH12 备用"]
CHANNEL_COLORS = ["#e74c3c", "#3498db", "#2ecc71", "#f39c12",
                  "#9b59b6", "#1abc9c", "#e67e22", "#95a5a6",
                  "#e91e63", "#00bcd4", "#ff9800", "#607d8b"]


# ============================================================
# UDP 接收器线程
# ============================================================
class RCReceiver(threading.Thread):
    def __init__(self, on_data, on_status):
        super().__init__(daemon=True)
        self.on_data = on_data
        self.on_status = on_status
        self.running = False
        self.sock = None
        self.rx_count = 0

    def start_server(self):
        self.running = True
        self.start()

    def stop_server(self):
        self.running = False
        if self.sock:
            try: self.sock.close()
            except: pass

    def run(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.sock.bind(("0.0.0.0", 10001))
            self.sock.settimeout(1.0)
            self.on_status("listening", "UDP 监听 10001 端口 ✓")
        except Exception as e:
            self.on_status("error", f"端口绑定失败: {e}")
            return

        while self.running:
            try:
                data, addr = self.sock.recvfrom(1024)
                self.rx_count += 1
            except socket.timeout:
                continue
            except:
                break

            try:
                payload = json.loads(data.decode("utf-8"))
            except:
                continue

            channels = {}
            for ch_str, raw_val in payload.items():
                if ch_str == "ts": continue
                try:
                    ch = int(ch_str.replace("ch", ""))
                except: continue
                if ch in AXIS_MAP:
                    # PWM 1000-2000 → vJoy 0x0000-0xFFFF
                    raw = float(raw_val)
                    pct = max(0.0, min(1.0, (raw - 1050.0) / 900.0))
                    vjoy_dev.set_axis(AXIS_MAP[ch], int(pct * 0xFFFF))
                    channels[ch] = pct * 100.0

            self.on_data(channels, self.rx_count)


# ============================================================
# GUI
# ============================================================
class RCBridgeGUI:
    def __init__(self):
        self.win = tk.Tk()
        self.win.title("RC Bridge - 摇杆接收端")
        self.win.geometry("540x620")
        self.win.configure(bg="#1a1a2e")
        self.win.resizable(False, False)

        self.receiver = None
        self.widgets = {}  # ch -> (val_label, bar_canvas, fill_rect, pct_label, center_line)

        self.build_ui()

    def build_ui(self):
        # 标题
        tk.Label(self.win, text="RC Bridge", font=("Arial", 22, "bold"),
                 fg="#00d4ff", bg="#1a1a2e").pack(pady=(12, 2))
        tk.Label(self.win, text="H12 Pro → PC 摇杆桥接", font=("Arial", 10),
                 fg="#888", bg="#1a1a2e").pack(pady=(0, 10))

        # 状态栏
        sf = tk.Frame(self.win, bg="#16213e", height=50)
        sf.pack(fill="x", padx=15, pady=(0, 8))

        self.led_canvas = tk.Canvas(sf, width=14, height=14, bg="#16213e", highlightthickness=0)
        self.led_canvas.place(x=12, y=18)
        self.led = self.led_canvas.create_oval(1, 1, 13, 13, fill="#555", outline="")

        self.status_text = tk.Label(sf, text="等待启动...", font=("Arial", 11), fg="#aaa", bg="#16213e")
        self.status_text.place(x=35, y=16)

        self.fps_label = tk.Label(sf, text="0 帧", font=("Arial", 10), fg="#888", bg="#16213e")
        self.fps_label.place(x=420, y=16)

        # vJoy 状态
        self.vjoy_label = tk.Label(sf, text="vJoy: ✓", font=("Arial", 9),
                                     fg="#0f0", bg="#16213e")
        self.vjoy_label.place(x=460, y=16)

        # 控制按钮
        bf = tk.Frame(self.win, bg="#1a1a2e")
        bf.pack(pady=(0, 8))

        self.start_btn = tk.Button(bf, text="▶ 启动接收", command=self.toggle_receiver,
                                    font=("Arial", 12, "bold"), bg="#00ac8c", fg="white",
                                    width=14, relief="flat", cursor="hand2")
        self.start_btn.pack(side="left", padx=4)

        tk.Button(bf, text="✕ 退出", command=self.win.destroy,
                  font=("Arial", 12), bg="#c0392b", fg="white",
                  width=8, relief="flat", cursor="hand2").pack(side="left", padx=4)

        # 通道显示区域
        df = tk.Frame(self.win, bg="#1a1a2e")
        df.pack(fill="both", expand=True, padx=15)

        # 列表头
        hdr = tk.Frame(df, bg="#16213e")
        hdr.pack(fill="x", pady=(0, 4))
        for i, t in enumerate(["通道", "名称", "值", "摇杆位置"]):
            tk.Label(hdr, text=t, font=("Arial", 9, "bold"), fg="#888",
                     bg="#16213e",
                     width=6 if i == 0 else 12 if i == 1 else 6 if i == 2 else 22,
                     anchor="w" if i == 3 else "center").pack(side="left")

        # 通道条
        for ch in range(1, 13):
            f = tk.Frame(df, bg="#1a1a2e", pady=2)
            f.pack(fill="x")

            tk.Label(f, text=f"CH{ch}", font=("Arial", 11, "bold"),
                     fg=CHANNEL_COLORS[ch-1], bg="#1a1a2e", width=5, anchor="center").pack(side="left")

            tk.Label(f, text=CHANNEL_NAMES[ch-1], font=("Arial", 9),
                     fg="#ccc", bg="#1a1a2e", width=12, anchor="w").pack(side="left")

            val_lb = tk.Label(f, text="---", font=("Arial", 10, "bold"),
                               fg="#0f0", bg="#1a1a2e", width=5, anchor="e")
            val_lb.pack(side="left", padx=(0, 3))

            bar = tk.Canvas(f, width=220, height=18, bg="#0d0d1a",
                            highlightthickness=1, highlightbackground="#333")
            bar.pack(side="left")
            center = bar.create_line(110, 0, 110, 18, fill="#555", width=1, dash=(2, 2))
            fill = bar.create_rectangle(0, 0, 0, 18, fill=CHANNEL_COLORS[ch-1], outline="")

            pct_lb = tk.Label(f, text="0%", font=("Arial", 9), fg="#888", bg="#1a1a2e", width=5, anchor="w")
            pct_lb.pack(side="left")

            self.widgets[ch] = (val_lb, bar, fill, pct_lb, 110)

        # 底部提示
        tk.Label(self.win, text="提示: 打开飞行模拟器后选 vJoy Device 作为控制器",
                 font=("Arial", 9), fg="#555", bg="#1a1a2e").pack(pady=(6, 8))

    def set_status(self, level, text):
        colors = {"ready": "#0f0", "listening": "#0f0", "receiving": "#0f0",
                  "error": "#f00", "stopped": "#555"}
        self.led_canvas.itemconfig(self.led, fill=colors.get(level, "#555"))
        self.status_text.configure(text=text)

    def toggle_receiver(self):
        if self.receiver and self.receiver.running:
            self.receiver.stop_server()
            self.receiver = None
            self.start_btn.configure(text="▶ 启动接收", bg="#00ac8c")
            self.set_status("stopped", "已停止")
        else:
            self.receiver = RCReceiver(self.on_data, self.on_status)
            self.receiver.start_server()
            self.start_btn.configure(text="■ 停止", bg="#c0392b")

    def on_status(self, level, text):
        self.win.after(0, self.set_status, level, text)

    def on_data(self, channels, rx_count):
        def update():
            self.fps_label.configure(text=f"{rx_count} 帧")
            self.set_status("receiving", f"接收中...")
            for ch in range(1, 13):
                val_lb, bar, fill, pct_lb, center = self.widgets[ch]
                if ch in channels:
                    pct = channels[ch]
                    val_lb.configure(text=f"{pct:.0f}%")
                    pct_lb.configure(text=f"{pct:.0f}%")
                    bw = 220
                    fw = int(abs(pct - 50) * 4.4)
                    if pct >= 50:
                        bar.coords(fill, center, 0, min(center + fw, bw), 18)
                    else:
                        bar.coords(fill, max(center - fw, 0), 0, center, 18)
                else:
                    val_lb.configure(text="---")
                    pct_lb.configure(text="0%")
                    bar.coords(fill, 0, 0, 0, 18)
        self.win.after(0, update)

    def run(self):
        self.win.mainloop()


if __name__ == "__main__":
    try:
        init_vjoy()
        print("[RC Bridge] vJoy OK, 启动 GUI...")
    except Exception as e:
        print(f"[RC Bridge] vJoy 初始化失败: {e}")
        print("请先安装 vJoy 驱动: https://sourceforge.net/projects/vjoystick/")
        input("按 Enter 退出...")
        sys.exit(1)

    app = RCBridgeGUI()
    app.run()
