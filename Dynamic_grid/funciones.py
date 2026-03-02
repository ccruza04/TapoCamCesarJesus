import cv2
import json
import re
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, unquote

from PyQt6.QtCore import QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

try:
    from pytapo import Tapo
except ModuleNotFoundError:
    Tapo = None

RED_BASE = "192.168.60."
RECORD_FPS = 15
PING_TIMEOUT_MS = 400
CONNECTION_CHECK_INTERVAL_MS = 60_000
SETTINGS_FILE = "settings.json"


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
    def __init__(self, mac, usuario, password, settings=None):
        super().__init__(daemon=True, name=f"CameraStream-{mac}")
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
        self.settings = settings or {}

    def _get_media_output_dir(self):
        configured_dir = str(self.settings.get("media_directory", "")).strip()
        output_dir = Path(configured_dir) if configured_dir else Path(__file__).resolve().parent
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    def _build_media_filename(self, prefix, extension):
        camera_id = (self.ip or self.mac or "camara").replace(":", "-")
        captured_at = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{prefix}_{camera_id}_{captured_at}.{extension}"

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
                output_dir = self._get_media_output_dir()
                filename = output_dir / self._build_media_filename("video", "mp4")
                self.out = cv2.VideoWriter(
                    str(filename),
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

    def capture_photo(self):
        with self.capture_lock:
            if self.frame is None:
                return False, "Sin imagen disponible"
            frame_copy = self.frame.copy()

        output_dir = self._get_media_output_dir()
        photo_path = output_dir / self._build_media_filename("foto", "jpg")
        saved = cv2.imwrite(str(photo_path), frame_copy)
        if not saved:
            return False, "No se pudo guardar la foto"
        return True, str(photo_path)


    def set_settings(self, settings):
        self.settings = settings

    def get_tapo_client(self):
        if Tapo is None:
            raise RuntimeError("Falta el módulo 'pytapo'. Instala con: pip install pytapo")

        if not self.ip:
            raise RuntimeError("La cámara todavía no tiene IP asignada")

        tapo_user = self.settings.get("tapo_user", "").strip() or self.usuario_raw
        tapo_password = self.settings.get("tapo_password", "").strip() or self.password_raw
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

        self.setObjectName("cameraCard")

        self.label = QLabel("Conectando…", alignment=Qt.AlignmentFlag.AlignCenter)
        self.label.setObjectName("videoLabel")

        self.status = QLabel("⏳ Iniciando…")
        self.status.setObjectName("statusLabel")

        self.btn_record = QPushButton("⏺ Grabar")
        self.btn_record.clicked.connect(self.on_toggle_record)

        self.btn_capture = QPushButton("📸 Capturar")
        self.btn_capture.clicked.connect(self.on_capture_photo)

        btns = QHBoxLayout()
        btns.addStretch()
        btns.addWidget(self.btn_record)
        btns.addWidget(self.btn_capture)
        btns.addStretch()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        layout.addWidget(self.status)
        layout.addWidget(self.label, stretch=1)
        layout.addLayout(btns)

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
            self.btn_record.setText("⏺ Grabar")
            return

        if self.feed.recording:
            self.btn_record.setText("⏹ Detener")
            self.status.setText("🔴 Grabando")
        else:
            self.btn_record.setText("⏺ Grabar")

    def on_capture_photo(self):
        ok, message = self.feed.capture_photo()
        if ok:
            self.status.setText(f"📸 Foto guardada: {message}")
        else:
            self.status.setText(f"❌ {message}")

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
    action_result = pyqtSignal(str)

    def __init__(self, feed):
        super().__init__()
        self.setWindowTitle(f"Cámara {feed.ip or feed.mac}")
        self.resize(700, 480)
        self.feed = feed

        self.label = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        self.status = QLabel("Controles PTZ listos")
        self.action_result.connect(self.status.setText)

        self.btn_record = QPushButton("⏺ Grabar")
        self.btn_capture = QPushButton("📸 Capturar")

        layout = QVBoxLayout(self)
        media_actions = QHBoxLayout()
        media_actions.addStretch()
        media_actions.addWidget(self.btn_record)
        media_actions.addWidget(self.btn_capture)
        media_actions.addStretch()

        layout.addLayout(media_actions)
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
        ]:
            btn.setFixedSize(52, 40)
            btn.setObjectName("padButton")

        for btn in [self.btn_zoom_in, self.btn_zoom_out]:
            btn.setFixedSize(84, 32)
            btn.setObjectName("zoomButton")

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
        self.btn_record.clicked.connect(self.on_toggle_record)
        self.btn_capture.clicked.connect(self.on_capture_photo)

        if Tapo is None:
            self._set_ptz_enabled(False)
            self.status.setText("⚠️ PTZ deshabilitado: instala pytapo")

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(40)

    def _set_ptz_enabled(self, enabled):
        controls = [
            self.btn_up,
            self.btn_down,
            self.btn_left,
            self.btn_right,
            self.btn_center,
            self.btn_zoom_in,
            self.btn_zoom_out,
        ]
        for control in controls:
            control.setEnabled(enabled)

    def _run_camera_action(self, action, success_message):
        def worker():
            try:
                action()
                self.action_result.emit(success_message)
            except Exception as exc:
                self.action_result.emit(f"❌ {exc}")

        threading.Thread(target=worker, daemon=True, name=f"PTZ-{self.feed.mac}").start()

    def send_move(self, x_axis, y_axis):
        self._run_camera_action(lambda: self.feed.move(x_axis, y_axis), "✅ Movimiento enviado")

    def send_zoom(self, zoom_in):
        message = "✅ Zoom + enviado" if zoom_in else "✅ Zoom - enviado"
        self._run_camera_action(lambda: self.feed.zoom(zoom_in), message)

    def on_toggle_record(self):
        ok = self.feed.toggle_record()
        if not ok:
            self.action_result.emit("❌ Error al iniciar grabación")
            self.btn_record.setText("⏺ Grabar")
            return
        self.btn_record.setText("⏹ Detener" if self.feed.recording else "⏺ Grabar")

    def on_capture_photo(self):
        ok, message = self.feed.capture_photo()
        self.action_result.emit(f"📸 Foto guardada: {message}" if ok else f"❌ {message}")

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
def save_settings(settings):
    settings_file = Path(__file__).with_name(SETTINGS_FILE)
    with settings_file.open("w", encoding="utf-8") as f:
        json.dump(settings, f, indent=4, ensure_ascii=False)


def update_settings(partial_settings):
    current_settings = load_settings()
    current_settings.update(partial_settings)
    save_settings(current_settings)
    return current_settings


def load_settings():
    settings_file = Path(__file__).with_name(SETTINGS_FILE)

    try:
        with settings_file.open("r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return {
                    "tapo_user": str(data.get("tapo_user", "")),
                    "tapo_password": str(data.get("tapo_password", "")),
                    "media_directory": str(data.get("media_directory", "")),
                }
    except FileNotFoundError:
        pass
    except json.JSONDecodeError:
        pass

    return {"tapo_user": "", "tapo_password": "", "media_directory": ""}


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



def load_cameras(settings=None):
    widgets = []
    data_file = Path(__file__).with_name("cameras.dat")

    try:
        with data_file.open("r", encoding="utf-8") as f:
            cams_data = json.load(f)
            for cam in cams_data:
                feed = CameraFeed(cam["mac"], cam["usuario"], cam["password"], settings=settings)
                feed.start()
                widget = CameraWidget(feed)
                widgets.append(widget)
    except FileNotFoundError:
        pass
    return widgets
