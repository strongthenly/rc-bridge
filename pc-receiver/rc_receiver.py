"""
RC Bridge - PC 接收端 (pyvjoy 版)
"""
import json, socket, time, logging, sys
try: import pyvjoy
except ImportError:
    print("pip install pyvjoy"); sys.exit(1)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("RCBridge")

UDP_PORT = 10001
VJOY_DEVICE_ID = 1

AXIS_MAP = {
    1: pyvjoy.HID_USAGE_X, 2: pyvjoy.HID_USAGE_Y,
    3: pyvjoy.HID_USAGE_Z, 4: pyvjoy.HID_USAGE_RX,
    5: pyvjoy.HID_USAGE_RY, 6: pyvjoy.HID_USAGE_RZ,
    7: pyvjoy.HID_USAGE_SL0, 8: pyvjoy.HID_USAGE_SL1,
}

def main():
    log.info("=" * 50)
    log.info("RC Bridge - PC 接收端")
    log.info(f"UDP 端口: {UDP_PORT}")
    log.info(f"vJoy 设备: #{VJOY_DEVICE_ID}")
    log.info("=" * 50)

    try:
        vjoy_dev = pyvjoy.VJoyDevice(VJOY_DEVICE_ID)
        log.info(f"vJoy 设备 #{VJOY_DEVICE_ID} 已连接")
    except Exception as e:
        log.error(f"vJoy 连接失败: {e}")
        log.error("请打开 Configure vJoy → Device 1 → 4 Axes → Apply")
        input("按 Enter 退出...")
        return

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.settimeout(1.0)
    try:
        sock.bind(("0.0.0.0", UDP_PORT))
        log.info(f"UDP 监听 0.0.0.0:{UDP_PORT}")
    except OSError as e:
        log.error(f"绑定端口失败: {e}"); return

    last_data_time = time.time()
    rx_count = 0
    log.info("等待摇杆数据... (在 H12 Pro 上启动 RC Bridge APP 并点启动广播)")

    try:
        while True:
            try:
                data, addr = sock.recvfrom(1024)
                last_data_time = time.time(); rx_count += 1
            except socket.timeout:
                continue

            try: payload = json.loads(data.decode("utf-8"))
            except: continue

            for ch_num_str, raw_value in payload.items():
                if ch_num_str == "ts" or not ch_num_str.startswith("ch"): continue
                try: ch_num = int(ch_num_str[2:])
                except: continue
                if ch_num not in AXIS_MAP: continue
                pct = max(0.0, min(1.0, float(raw_value) / 1000.0))
                vjoy_dev.set_axis(AXIS_MAP[ch_num], int(pct * 0xFFFF))

            if rx_count % 10 == 0:
                vals = []
                for ch in range(1, 9):
                    key = f"ch{ch}"
                    if key in payload:
                        pct = float(payload[key]) / 10.0
                        vals.append(f"CH{ch}={pct:.0f}%")
                print(f"\r{rx_count:5d}帧 | {'  '.join(vals)}", end="", flush=True)

    except KeyboardInterrupt: print()
    finally: sock.close(); log.info("已退出")

if __name__ == "__main__":
    main()
