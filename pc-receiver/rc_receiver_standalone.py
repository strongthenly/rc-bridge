"""
RC Bridge - PC 接收端 (独立版)
先释放 vJoy 设备，再监听 UDP
"""
import ctypes, json, socket, time, sys, os

# ===== 第1步: 强制释放 vJoy 设备 =====
dll_path = r"C:\Program Files\vJoy\x64\vJoyInterface.dll"
if os.path.exists(dll_path):
    dll = ctypes.CDLL(dll_path)
    dll.RelinquishVJD.argtypes = [ctypes.c_uint]
    dll.RelinquishVJD(1)
    dll.GetVJDStatus.argtypes = [ctypes.c_uint]
    dll.GetVJDStatus.restype = ctypes.c_uint
    dll.AcquireVJD.argtypes = [ctypes.c_uint]
    dll.AcquireVJD.restype = ctypes.c_bool
    
    # 再试几次直到获取成功
    for attempt in range(5):
        status = dll.GetVJDStatus(1)
        if status == 1:  # FREE
            if dll.AcquireVJD(1):
                print(f"[vJoy] Device 1 acquired (attempt {attempt+1})")
                dll.RelinquishVJD(1)
                print("[vJoy] Released - ready")
                break
        elif status == 2:  # BUSY
            dll.RelinquishVJD(1)
        time.sleep(0.5)
    else:
        print("[vJoy] Cannot acquire device - still BUSY after 5 attempts")
        print("[vJoy] Open Configure vJoy → Device 1 → Reset")
else:
    print(f"[vJoy] DLL not found at {dll_path}")

# ===== 第2步: 导入 pyvjoy 并连接 =====
try:
    import pyvjoy
    vjoy_dev = pyvjoy.VJoyDevice(1)
    print("[vJoy] Connected successfully!")
except Exception as e:
    print(f"[vJoy] Failed: {e}")
    sys.exit(1)

# ===== 第3步: UDP 接收 =====
UDP_PORT = 10001
AXIS_MAP = {
    1: pyvjoy.HID_USAGE_X, 2: pyvjoy.HID_USAGE_Y,
    3: pyvjoy.HID_USAGE_Z, 4: pyvjoy.HID_USAGE_RX,
    5: pyvjoy.HID_USAGE_RY, 6: pyvjoy.HID_USAGE_RZ,
    7: pyvjoy.HID_USAGE_SL0, 8: pyvjoy.HID_USAGE_SL1,
}

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.settimeout(1.0)
sock.bind(("0.0.0.0", UDP_PORT))

print(f"[UDP] Listening on 0.0.0.0:{UDP_PORT}")
print("[等待] 在 H12 Pro 上打开 RC Bridge APP → 启动广播服务")
print("=" * 50)

rx_count = 0
last_ts = time.time()

try:
    while True:
        try:
            data, addr = sock.recvfrom(1024)
            rx_count += 1
            last_ts = time.time()
        except socket.timeout:
            continue

        try:
            payload = json.loads(data.decode("utf-8"))
        except:
            continue

        for ch_str, raw_val in payload.items():
            if ch_str == "ts" or not ch_str.startswith("ch"):
                continue
            try:
                ch = int(ch_str[2:])
            except:
                continue
            if ch not in AXIS_MAP:
                continue
            pct = max(0.0, min(1.0, float(raw_val) / 1000.0))
            vjoy_dev.set_axis(AXIS_MAP[ch], int(pct * 0xFFFF))

        if rx_count % 10 == 0:
            vals = []
            for ch in range(1, 9):
                k = f"ch{ch}"
                if k in payload:
                    vals.append(f"CH{ch}={float(payload[k])/10:.0f}%")
            print(f"\r收到 {rx_count:5d} 帧 | {'  '.join(vals[:4])}", end="", flush=True)

except KeyboardInterrupt:
    print("\n[退出]")
finally:
    sock.close()
    dll.RelinquishVJD(1)
    print("[完毕]")
