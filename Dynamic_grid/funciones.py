import cv2
import json
import re
import subprocess
import threading
import time
from pathlib import Path
from urllib.parse import quote, unquote

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

RED_BASE = "192.168.60."
RECORD_FPS = 15
PING_TIMEOUT_MS = 400
CONNECTION_CHECK_INTERVAL_MS = 60_000


def _decode_if_needed(value: str) -> str:
    """Permite cargar credenciales antiguas ya codificadas sin romper el login."""
    try:
        return unquote(value)
    except Exception:
        return value


# ---------------- BUSCAR IP ----------------
def buscar_ip_por_mac(mac: str):
    """Búsqueda de IP por MAC usando ping corto + ARP."""
    mac = mac.lower().replace(":", "-")
    for i in range(1, 255):
        ip = f"{RED_BASE}{i}"
        subprocess.call(
            f"ping -n 1 -w {PING_TIMEOUT_MS} {ip}",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=True,
        )
        salida = subprocess.check_output("arp -a", shell=True).decode("cp1252", errors="ignore")
        for linea in salida.splitlines():
            if mac in linea.lower():
                encontrada = re.findall(r"\d+\.\d+\.\d+\.\d+", linea)
                if encontrada:
                    return encontrada[0]
    return None


# ---------------- CAMERA THREAD ----------------
class CameraFeed(threading.Thread):
    def __init__(self, mac, usuario, password):
        super().__init__(daemon=True)
        self.mac = mac

        # Guardamos versiones sin codificar para persistencia
        self.usuario_raw = _decode_if_needed(usuario)
        self.password_raw = _decode_if_needed(password)

        self.usuario = quote(self.usuario_raw, safe="")
        self.password = quote(self.password_raw, safe="")
        self.ip = None
        self.rtsp_url = None
        self.frame = None

        self.capture_lock = threading.Lock()
        self.writer_lock = threading.Lock()

        self.recording = False
        self.out = None
        self.last_write = 0
        self.write_interval = 1 / RECORD_FPS

        self._stop_event = threading.Event()
        self._force_reconnect_event = threading.Event()
        self._last_ok_read = 0
        self.connected = False

    def run(self):
        self._connect_and_capture_loop()

    def stop(self):
        self._stop_event.set()
        self._force_reconnect_event.set()
        with self.writer_lock:
            if self.out is not None:
                self.out.release()
                self.out = None
                self.recording = False

    def request_reconnect(self):
        self._force_reconnect_event.set()

    def check_connection(self):
        """Comprueba conexión y fuerza reconexión si está caída."""
        if self._stop_event.is_set():
            return

        stale = (time.time() - self._last_ok_read) > 10
        if not self.connected or stale:
            self.request_reconnect()

    def _build_rtsp_url(self):
        if self.ip:
            self.rtsp_url = f"rtsp://{self.usuario}:{self.password}@{self.ip}:554/stream1"

    def _resolve_ip_if_needed(self):
        if self.ip is None:
            self.ip = buscar_ip_por_mac(self.mac)
            self._build_rtsp_url()

    def _connect_and_capture_loop(self):
        while not self._stop_event.is_set():
            self._resolve_ip_if_needed()
            if not self.rtsp_url:
                self.connected = False
                time.sleep(3)
                continue

            cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            if not cap.isOpened():
                self.connected = False
                cap.release()
                time.sleep(2)
                continue

            self.connected = True
            self._last_ok_read = time.time()
            self._force_reconnect_event.clear()

            while not self._stop_event.is_set():
                if self._force_reconnect_event.is_set():
                    self.connected = False
                    break

                ret, frame = cap.read()
                if not ret or frame is None or frame.size == 0:
                    self.connected = False
                    time.sleep(0.4)
                    break

                with self.capture_lock:
                    self.frame = frame

                self._last_ok_read = time.time()
                self.connected = True
                self._write_if_recording(frame)

            cap.release()
            self._force_reconnect_event.clear()
            time.sleep(1)

    def _write_if_recording(self, frame):
        with self.writer_lock:
            if self.recording and self.out:
                now = time.time()
                if now - self.last_write >= self.write_interval:
                    self.out.write(frame)
                    self.last_write = now

    def toggle_record(self):
        with self.writer_lock:
            if not self.recording and self.frame is not None:
                h, w, _ = self.frame.shape
                filename = f"grab_{self.ip or self.mac}_{int(time.time())}.mp4"
                self.out = cv2.VideoWriter(
                    filename,
                    cv2.VideoWriter_fourcc(*"mp4v"),
                    RECORD_FPS,
                    (w, h),
                )
                if not self.out.isOpened():
                    self.out = None
                    self.recording = False
                    return False

                self.recording = True
                self.last_write = time.time()
                return True

            self.recording = False
            if self.out:
                self.out.release()
                self.out = None
            return True


# ---------------- CAMERA WIDGET ----------------
class CameraWidget(QWidget):
    def __init__(self, feed):
        super().__init__()
        self.feed = feed

        self.setObjectName("cameraCard")

        self.label = QLabel("Conectando…", alignment=Qt.AlignmentFlag.AlignCenter)
        self.label.setObjectName("videoLabel")

        self.status = QLabel("⏳ Iniciando…")
        self.status.setObjectName("statusLabel")

        self.btn = QPushButton("⏺ Grabar")
        self.btn.clicked.connect(self.on_toggle_record)

        btns = QHBoxLayout()
        btns.addStretch()
        btns.addWidget(self.btn)
        btns.addStretch()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        layout.addWidget(self.status)
        layout.addWidget(self.label, stretch=1)
        layout.addLayout(btns)

        # doble click abre ventana independiente
        self.label.mouseDoubleClickEvent = self.open_window
        self.cam_window = None

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(40)

        self.connection_timer = QTimer()
        self.connection_timer.timeout.connect(self._minute_connection_check)
        self.connection_timer.start(CONNECTION_CHECK_INTERVAL_MS)

    def _minute_connection_check(self):
        self.feed.check_connection()

    def on_toggle_record(self):
        ok = self.feed.toggle_record()
        if not ok:
            self.status.setText("❌ Error al iniciar grabación")
            self.btn.setText("⏺ Grabar")
            return

        if self.feed.recording:
            self.btn.setText("⏹ Detener")
            self.status.setText("🔴 Grabando")
        else:
            self.btn.setText("⏺ Grabar")

    def update_frame(self):
        if self.feed.frame is not None:
            with self.feed.capture_lock:
                frame = self.feed.frame.copy()

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = QImage(
                rgb.data,
                rgb.shape[1],
                rgb.shape[0],
                rgb.strides[0],
                QImage.Format.Format_RGB888,
            )
            self.label.setPixmap(
                QPixmap.fromImage(img).scaled(
                    self.label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            self.status.setText(
                f"🟢 En línea | IP: {self.feed.ip or 'resolviendo'}"
                + (" | 🔴 Grabando" if self.feed.recording else "")
            )
        else:
            self.status.setText("🟡 Sin imagen, reconectando…")

    def open_window(self, event):
        if self.cam_window is None:
            self.cam_window = CameraWindow(self.feed)
        self.cam_window.show()


# ---------------- CAMERA WINDOW ----------------
class CameraWindow(QWidget):
    def __init__(self, feed):
        super().__init__()
        self.setWindowTitle(f"Cámara {feed.ip or feed.mac}")
        self.resize(640, 480)
        self.feed = feed
        self.label = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        layout = QVBoxLayout(self)
        layout.addWidget(self.label)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(40)

    def update_frame(self):
        if self.feed.frame is not None:
            with self.feed.capture_lock:
                frame = self.feed.frame.copy()

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = QImage(
                rgb.data,
                rgb.shape[1],
                rgb.shape[0],
                rgb.strides[0],
                QImage.Format.Format_RGB888,
            )
            self.label.setPixmap(
                QPixmap.fromImage(img).scaled(
                    self.label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )


# ---------------- GUARDAR Y CARGAR ----------------
def save_cameras(widgets):
    cams_data = []
    for w in widgets:
        cam = {
            "mac": w.feed.mac,
            "usuario": w.feed.usuario_raw,
            "password": w.feed.password_raw,
        }
        cams_data.append(cam)

    data_file = Path(__file__).with_name("cameras.dat")
    with data_file.open("w", encoding="utf-8") as f:
        json.dump(cams_data, f, indent=4, ensure_ascii=False)


def load_cameras():
    widgets = []
    data_file = Path(__file__).with_name("cameras.dat")

    try:
        with data_file.open("r", encoding="utf-8") as f:
            cams_data = json.load(f)
            for cam in cams_data:
                feed = CameraFeed(cam["mac"], cam["usuario"], cam["password"])
                feed.start()
                widget = CameraWidget(feed)
                widgets.append(widget)
    except FileNotFoundError:
        pass
    return widgets
