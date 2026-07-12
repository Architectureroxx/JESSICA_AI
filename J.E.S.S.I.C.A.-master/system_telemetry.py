import time
import socket
import json
import psutil

TELEMETRY_HOST = "127.0.0.1"
TELEMETRY_PORT = 6666

def stream_system_telemetry():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server_socket.bind((TELEMETRY_HOST, TELEMETRY_PORT))
        server_socket.listen(1)
        print(f"[Telemetry Core] Broadcasting stream on {TELEMETRY_HOST}:{TELEMETRY_PORT}")
    except Exception as e:
        print(f"[-] Telemetry initialization error: {e}")
        return

    while True:
        try:
            client_conn, addr = server_socket.accept()
            while True:
                metrics = {
                    "cpu": psutil.cpu_percent(),
                    "ram": psutil.virtual_memory().percent,
                    "disk": psutil.disk_usage('/').percent
                }
                serialized_payload = json.dumps(metrics) + "\n"
                client_conn.sendall(serialized_payload.encode('utf-8'))
                time.sleep(0.5) # Fast 500ms sampling rate
        except Exception:
            time.sleep(2) # Auto-reconnect safety loop

if __name__ == "__main__":
    stream_system_telemetry()