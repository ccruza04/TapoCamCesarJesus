import cv2
import json
import random
import re
import subprocess
import threading
import time
from urllib.parse import quote

from pytapo import Tapo
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

RED_BASE = "192.168.60."
RECORD_FPS = 15
CAMERAS_FILE = "cameras.dat"
SETTINGS_FILE = "settings.dat"


# ---------------- BUSCAR IP ----------------
def buscar_ip_por_mac(mac):
    """Búsqueda rápida de IP por MAC usando ping de 1 intento"""
    mac = mac.lower().replace(":", "-")
    for i in range(1, 255):
        ip = f"{RED_BASE}{i}"
        subprocess.call(
            f"ping -n 1 -w 20 {ip}",
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


# ---------------- AJUSTES ----------------
def default_settings():
    return {"tapo_user": "", "tapo_password": ""}


def load_settings():
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.loads(f.read())
            return {
                "tapo_user": data.get("tapo_user", ""),
                "tapo_password": data.get("tapo_password", ""),
            }
    except FileNotFoundError:
        return default_settings()


def save_settings(settings):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        f.write(json.dumps(settings, indent=4))


# ---------------- CAMERA THREAD ----------------
class CameraFeed(threading.Thread):
    def __init__(self, mac, usuario, password, settings=None):
        super().__init__(daemon=True)
        self.mac = mac
        self.usuario = usuario
        self.password = password
        self.settings = settings or default_settings()

        self.ip = None
        self.rtsp_url = None
        self.frame = None
        self.recording = False
        self.out = None
        self.last_write = 0
        self.write_interval = 1 / RECORD_FPS

        threading.Thread(target=self.init_ip_and_rtsp, daemon=True).start()

    def init_ip_and_rtsp(self):
        self.ip = buscar_ip_por_mac(self.mac)
        if self.ip:
            user_quoted = quote(self.usuario, safe="")
            pass_quoted = quote(self.password, safe="")
            self.rtsp_url = f"rtsp://{user_quoted}:{pass_quoted}@{self.ip}:554/stream1"
            threading.Thread(target=self.run_capture, daemon=True).start()

    def run_capture(self):
        if not self.rtsp_url:
            return

        while True:
            cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            while True:
                ret, frame = cap.read()
                if not ret or frame is None or frame.size == 0:
                    cap.release()
                    time.sleep(1)
                    break

                self.frame = frame

                if self.recording and self.out:
                    now = time.time()
                    if now - self.last_write >= self.write_interval:
                        self.out.write(frame)
                        self.last_write = now

    def toggle_record(self):
        if not self.recording and self.frame is not None:
            h, w, _ = self.frame.shape
            self.out = cv2.VideoWriter(
                f"grab_{self.ip}_{int(time.time())}.mp4",
                cv2.VideoWriter_fourcc(*"mp4v"),
                RECORD_FPS,
                (w, h),
            )
            self.recording = True
        else:
            self.recording = False
            if self.out:
                self.out.release()
                self.out = None

    def set_settings(self, settings):
        self.settings = settings

    def get_tapo_client(self):
        if not self.ip:
            raise RuntimeError("La cámara todavía no tiene IP asignada")

        tapo_user = self.settings.get("tapo_user", "").strip() or self.usuario
        tapo_password = self.settings.get("tapo_password", "").strip() or self.password
        return Tapo(self.ip, tapo_user, tapo_password)

    def _call_first_available(self, client, method_names, *args):
        for method_name in method_names:
            method = getattr(client, method_name, None)
            if callable(method):
                return method(*args)
        raise AttributeError(f"Ningún método disponible entre: {', '.join(method_names)}")

    def move(self, x_axis, y_axis):
        client = self.get_tapo_client()
        self._call_first_available(client, ["moveMotor", "move_motor", "move"], x_axis, y_axis)

    def zoom(self, zoom_in):
        client = self.get_tapo_client()
        if zoom_in:
            self._call_first_available(client, ["zoomIn", "zoom_in"])
        else:
            self._call_first_available(client, ["zoomOut", "zoom_out"])


# ---------------- CAMERA WIDGET ----------------
class CameraWidget(QWidget):
    def __init__(self, feed):
        super().__init__()
        self.feed = feed
        accent = random.choice(["#38BDF8", "#A7F3D0", "#FDE68A", "#FCA5A5"])

        self.setStyleSheet(
            f"""
        QWidget {{
            background-color: #111827;
            border-radius: 12px;
            border: 2px solid {accent};
        }}
        """
        )

        self.label = QLabel("Cargando...", alignment=Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("background:black; border-radius:8px; color:white;")

        self.btn = QPushButton("⏺ Grabar")
        self.btn.clicked.connect(self.feed.toggle_record)

        btns = QHBoxLayout()
        btns.addStretch()
        btns.addWidget(self.btn)
        btns.addStretch()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        layout.addWidget(self.label, stretch=1)
        layout.addLayout(btns)

        self.label.mouseDoubleClickEvent = self.open_window
        self.cam_window = None

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(40)

    def update_frame(self):
        if self.feed.frame is not None:
            rgb = cv2.cvtColor(self.feed.frame, cv2.COLOR_BGR2RGB)
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

    def open_window(self, event):
        if self.cam_window is None:
            self.cam_window = CameraWindow(self.feed)
        self.cam_window.show()


# ---------------- CAMERA WINDOW ----------------
class CameraWindow(QWidget):
    def __init__(self, feed):
        super().__init__()
        self.setWindowTitle(f"Cámara {feed.ip or feed.mac}")
        self.resize(760, 540)
        self.feed = feed

        self.label = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        self.status = QLabel("Controles PTZ listos")

        layout = QVBoxLayout(self)
        layout.addWidget(self.label, stretch=1)

        controls_container = QWidget()
        controls_layout = QGridLayout(controls_container)
        controls_layout.setHorizontalSpacing(8)
        controls_layout.setVerticalSpacing(8)

        self.btn_up = QPushButton("▲")
        self.btn_down = QPushButton("▼")
        self.btn_left = QPushButton("◀")
        self.btn_right = QPushButton("▶")
        self.btn_center = QPushButton("●")

        self.btn_zoom_in = QPushButton("Zoom +")
        self.btn_zoom_out = QPushButton("Zoom -")

        for btn in [
            self.btn_up,
            self.btn_down,
            self.btn_left,
            self.btn_right,
            self.btn_center,
            self.btn_zoom_in,
            self.btn_zoom_out,
        ]:
            btn.setFixedSize(90, 34)

        controls_layout.addWidget(self.btn_up, 0, 1)
        controls_layout.addWidget(self.btn_left, 1, 0)
        controls_layout.addWidget(self.btn_center, 1, 1)
        controls_layout.addWidget(self.btn_right, 1, 2)
        controls_layout.addWidget(self.btn_down, 2, 1)
        controls_layout.addWidget(self.btn_zoom_in, 0, 3)
        controls_layout.addWidget(self.btn_zoom_out, 1, 3)

        layout.addWidget(controls_container, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status)

        self.btn_up.clicked.connect(lambda: self.send_move(0, 1))
        self.btn_down.clicked.connect(lambda: self.send_move(0, -1))
        self.btn_left.clicked.connect(lambda: self.send_move(-1, 0))
        self.btn_right.clicked.connect(lambda: self.send_move(1, 0))
        self.btn_center.clicked.connect(lambda: self.send_move(0, 0))
        self.btn_zoom_in.clicked.connect(lambda: self.send_zoom(True))
        self.btn_zoom_out.clicked.connect(lambda: self.send_zoom(False))

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(40)

    def update_frame(self):
        if self.feed.frame is not None:
            rgb = cv2.cvtColor(self.feed.frame, cv2.COLOR_BGR2RGB)
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

    def send_move(self, x_axis, y_axis):
        self.status.setText("Enviando movimiento...")

        def worker():
            try:
                self.feed.move(x_axis, y_axis)
                self.status.setText("Movimiento aplicado")
            except Exception as exc:
                self.status.setText(f"Error PTZ: {exc}")

        threading.Thread(target=worker, daemon=True).start()

    def send_zoom(self, zoom_in):
        self.status.setText("Aplicando zoom...")

        def worker():
            try:
                self.feed.zoom(zoom_in)
                self.status.setText("Zoom aplicado")
            except Exception as exc:
                self.status.setText(f"Error zoom: {exc}")

        threading.Thread(target=worker, daemon=True).start()


# ---------------- GUARDAR Y CARGAR ----------------
def save_cameras(widgets):
    cams_data = []
    for w in widgets:
        cam = {"mac": w.feed.mac, "usuario": w.feed.usuario, "password": w.feed.password}
        cams_data.append(cam)
    with open(CAMERAS_FILE, "w", encoding="utf-8") as f:
        f.write(json.dumps(cams_data, indent=4))


def load_cameras(settings=None):
    widgets = []
    try:
        with open(CAMERAS_FILE, "r", encoding="utf-8") as f:
            cams_data = json.loads(f.read())
            for cam in cams_data:
                feed = CameraFeed(cam["mac"], cam["usuario"], cam["password"], settings=settings)
                widget = CameraWidget(feed)
                widgets.append(widget)
    except FileNotFoundError:
        pass
    return widgets
