# main.py — AP + servidor HTTP que muestra el valor del ADC0 (GP26) en tiempo real
import network, socket, gc, time
from machine import Pin, ADC

# =================== CONFIGURACIÓN AP ===================
SSID     = "PicoW-AP-GRUPO2"
PASSWORD = "12345678"
CHANNEL  = 8
IP       = "192.168.4.1"
MASK     = "255.255.255.0"
GW       = "192.168.4.1"
DNS      = "8.8.8.8"

HTML_FILE = "indexmodificado.html"

# =================== HARDWARE ====================
LED = Pin("LED", Pin.OUT)
LED.value(0)
adc0 = ADC(0)  # GP26 (ADC0)

# =================== HTTP UTILS ==================
def http_send(conn, status="200 OK", ctype="text/html; charset=utf-8", body=b"", extra_headers=None):
    try:
        hdr = "HTTP/1.1 {}\r\nContent-Type: {}\r\nConnection: close\r\n".format(status, ctype)
        if extra_headers:
            for k, v in extra_headers.items():
                hdr += "{}: {}\r\n".format(k, v)
        hdr += "\r\n"
        conn.sendall(hdr.encode())
        if body:
            if isinstance(body, str):
                body = body.encode()
            conn.sendall(body)
    except Exception:
        pass

def http_redirect(conn, location="/"):
    http_send(conn, "302 Found", "text/plain; charset=utf-8", "Redirecting...", {"Location": location})

def read_request(conn):
    try:
        data = conn.recv(1024)
    except Exception:
        return None, None, b""
    if not data:
        return None, None, b""
    try:
        head, _ = data.split(b"\r\n\r\n", 1) if b"\r\n\r\n" in data else (data, b"")
        first = head.split(b"\r\n", 1)[0].decode()
        parts = first.split()
        method = parts[0] if len(parts) > 0 else "GET"
        target = parts[1] if len(parts) > 1 else "/"
        return method, target, head
    except Exception:
        return None, None, b""

def split_path_query(target):
    if not target:
        return "/", {}
    if "?" in target:
        path, qs = target.split("?", 1)
    else:
        path, qs = target, ""
    params = {}
    if qs:
        for pair in qs.split("&"):
            if not pair:
                continue
            if "=" in pair:
                k, v = pair.split("=", 1)
            else:
                k, v = pair, ""
            params[k] = v
    return path, params

# =================== AP ==========================
def start_ap():
    ap = network.WLAN(network.AP_IF)
    ap.active(False)
    time.sleep(0.1)
    try:
        ap.config(ssid=SSID, password=PASSWORD, channel=CHANNEL)
    except TypeError:
        ap.config(essid=SSID, password=PASSWORD, channel=CHANNEL)
    ap.ifconfig((IP, MASK, GW, DNS))
    ap.active(True)
    while not ap.active():
        time.sleep(0.05)
    return ap

# =================== CARGA HTML ==================
def load_index():
    try:
        with open(HTML_FILE, "rb") as f:
            return f.read()
    except OSError:
        return b"""<!doctype html>
<html><head><meta charset="utf-8"><title>index.html no encontrado</title></head>
<body><h3>Sube <code>index.html</code> a la raíz del dispositivo.</h3></body></html>"""

# =================== SERVIDOR ======================
def serve(index_bytes):
    addr = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(addr)
    srv.listen(3)
    print("HTTP en http://{}/".format(IP))

    while True:
        try:
            conn, remote = srv.accept()
            method, target, _ = read_request(conn)
            if not target:
                http_send(conn, "400 Bad Request", "text/plain; charset=utf-8", "Bad Request")
                conn.close(); gc.collect(); continue

            path, params = split_path_query(target)

            # Ruido navegador
            if path == "/favicon.ico":
                http_send(conn, "204 No Content", "text/plain; charset=utf-8", "")
                conn.close(); gc.collect(); continue

            # --- LED ON / OFF ---
            if path == "/on":
                LED.value(1)
                http_send(conn, "200 OK", "application/json; charset=utf-8", b'{"ok":true,"on":true}')
                conn.close(); gc.collect(); continue

            if path == "/off":
                LED.value(0)
                http_send(conn, "200 OK", "application/json; charset=utf-8", b'{"ok":true,"on":false}')
                conn.close(); gc.collect(); continue

            # Estado LED JSON
            if path == "/state":
                body = b'{"on":%s}' % (b"true" if LED.value() else b"false")
                http_send(conn, "200 OK", "application/json; charset=utf-8", body,
                          {"Cache-Control":"no-cache"})
                conn.close(); gc.collect(); continue

            # === Lectura ADC0 ===
            if path == "/adc":
                valor = adc0.read_u16()  # 0–65535
                voltaje = valor * 3.3 / 65535  # Conversión a voltios
                body = '{{"adc":{},"voltaje":{:.3f}}}'.format(valor, voltaje)
                http_send(conn, "200 OK", "application/json; charset=utf-8", body)
                conn.close(); gc.collect(); continue

            # Raíz -> index.html
            http_send(conn, "200 OK", "text/html; charset=utf-8", index_bytes,
                      {"Cache-Control":"no-cache"})
            conn.close()

        except Exception as e:
            try:
                http_send(conn, "500 Internal Server Error", "text/plain; charset=utf-8", "Internal Error")
                conn.close()
            except Exception:
                pass
        finally:
            gc.collect()

# =================== MAIN =======================
if __name__ == "__main__":
    ap = start_ap()
    print("AP activo  SSID:", SSID, "| IP:", ap.ifconfig()[0], "| Canal:", CHANNEL)
    index_bytes = load_index()
    serve(index_bytes)