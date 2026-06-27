"""
RC Bridge - ViGEmBus 版
用虚拟 Xbox 手柄替代 vJoy，兼容性更好，不需配置轴映射
"""
import json, socket, time, threading, struct
import vgamepad as vg

# ============================================================
# 配置
# ============================================================
UDP_PORT = 10001
# 死区：摇杆在 1500±DEADZONE 范围内视为中位
# 大多数遥控器物理回中偏差在 ±10~±30 之间
DEADZONE = 20  # 如果偏多可以加大，建议 15~40
# Xbox 手柄轴映射 (通道 → 手柄轴)
# 标准穿越机映射:
#   CH1 Roll  → 右摇杆 X
#   CH2 Pitch → 右摇杆 Y
#   CH3 Throttle → 左摇杆 Y (油门)
#   CH4 Yaw   → 左摇杆 X
CHANNEL_MAP = {
    1: "roll",     # 右摇杆 X
    2: "pitch",    # 右摇杆 Y
    3: "throttle", # 左摇杆 Y
    4: "yaw",      # 左摇杆 X
}
# 按键映射 (CH7~CH10 开关 → Xbox 按钮)
BUTTON_MAP = {
    7: vg.XUSB_BUTTON.XUSB_GAMEPAD_A,
    8: vg.XUSB_BUTTON.XUSB_GAMEPAD_B,
    9: vg.XUSB_BUTTON.XUSB_GAMEPAD_X,
    10: vg.XUSB_BUTTON.XUSB_GAMEPAD_Y,
}


class VigemBridge:
    def __init__(self):
        self.gamepad = vg.VX360Gamepad()
        self.running = False
        self.udp_rx = 0

    def pwm_to_axis(self, pwm_val: float) -> int:
        """PWM 1050~1950 → Xbox 轴值 0~32767 (中心 16384)，含死区"""
        # 死区处理：在 1500±DEADZONE 内强行输出中心
        if abs(pwm_val - 1500) <= DEADZONE:
            return 16384
        pct = max(0.0, min(1.0, (pwm_val - 1050.0) / 900.0))
        return int(pct * 32767)

    def pwm_to_trigger(self, pwm_val: float) -> int:
        """PWM 1050~1950 → 扳机值 0~255"""
        pct = max(0.0, min(1.0, (pwm_val - 1050.0) / 900.0))
        return int(pct * 255)

    def update(self, channels: dict):
        g = self.gamepad
        # 先收集所有轴值
        axes = {"lx": 0.0, "ly": 0.0, "rx": 0.0, "ry": 0.0}
        for ch, val in channels.items():
            if ch in CHANNEL_MAP:
                axis = CHANNEL_MAP[ch]
                v = (self.pwm_to_axis(val) / 32767) * 2 - 1  # -1.0 ~ 1.0
                if axis == "roll":    axes["rx"] = v
                elif axis == "pitch": axes["ry"] = v
                elif axis == "yaw":   axes["lx"] = v
                elif axis == "throttle": axes["ly"] = v

            elif ch in BUTTON_MAP:
                btn = BUTTON_MAP[ch]
                if val >= 1500:
                    g.press_button(button=btn)
                else:
                    g.release_button(button=btn)

        # 一次设置两个摇杆
        g.left_joystick_float(x_value_float=axes["lx"], y_value_float=axes["ly"])
        g.right_joystick_float(x_value_float=axes["rx"], y_value_float=axes["ry"])

        # 油门复用左扳机
        if 3 in channels:
            t = self.pwm_to_trigger(channels[3])
            g.left_trigger_float(value_float=t / 255.0)

        g.update()

    def run(self):
        self.running = True
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("0.0.0.0", UDP_PORT))
        sock.settimeout(1.0)

        last_print = time.time()
        while self.running:
            try:
                data, addr = sock.recvfrom(1024)
                self.udp_rx += 1
            except socket.timeout:
                continue

            try:
                payload = json.loads(data.decode("utf-8"))
            except:
                continue

            channels = {}
            for k, v in payload.items():
                if k == "ts": continue
                try:
                    ch = int(k.replace("ch", ""))
                    channels[ch] = float(v)
                except:
                    pass

            self.update(channels)

            # 打印状态 (每秒1次)
            now = time.time()
            if now - last_print >= 1.0:
                raw_vals = '  '.join(
                    f"CH{ch}={channels.get(ch, 1500):.0f}"
                    for ch in [1, 2, 3, 4]
                )
                deadzone_active = '  '.join(
                    f"CH{ch}✓" if abs(channels.get(ch, 1500) - 1500) <= DEADZONE else f"CH{ch}✗"
                    for ch in [1, 2, 3, 4]
                )
                print(f"\r{self.udp_rx:5d}帧/s | {raw_vals} | 死区{deadzone_active}", end="", flush=True)
                self.udp_rx = 0
                last_print = now

        sock.close()

    def stop(self):
        self.running = False


if __name__ == "__main__":
    print("=" * 50)
    print("RC Bridge - ViGEmBus 版")
    print("虚拟 Xbox 360 手柄 (无需配置)")
    print(f"UDP 端口: {UDP_PORT}")
    print("=" * 50)
    print("请在 H12 Pro 上启动 RC Bridge APP → 启动广播服务")
    print()

    bridge = VigemBridge()
    try:
        bridge.run()
    except KeyboardInterrupt:
        print("\n已退出")
