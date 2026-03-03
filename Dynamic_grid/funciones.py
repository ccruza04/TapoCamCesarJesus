import cv2
import json
import re
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

try:
    from pytapo import Tapo
except ModuleNotFoundError:
    Tapo = None

try:
    import mediapipe as mp
except ModuleNotFoundError:
    mp = None

RED_BASE = "192.168.60."
RECORD_FPS = 15
AUTO_RECORD_SECONDS = 30
GESTURE_STABLE_SECONDS = 0.3
GESTURE_COOLDOWN_SECONDS = 1.0
TRACK_COMMAND_INTERVAL = 0.25
GESTURE_FRAME_SKIP = 3
GESTURE_PROCESS_INTERVAL = 1 / 12
TRACK_DEAD_ZONE = 0.08
TRACK_MAX_STEP = 2
PAN_STEP = 10
TILT_STEP = 10
PING_TIMEOUT_MS = 400
CONNECTION_CHECK_INTERVAL_MS = 60_000
SETTINGS_FILE = "settings.json"


class GestureDetector:
    """Detecta gesto pistola usando MediaPipe Hands."""

    def __init__(self):
        self.available = mp is not None
        self._gesture_started_at = None
        self._active_until = 0
        self._cooldown_until = 0
        self._last_result = {
            "gesture_active": False,
            "tracking_confidence": 0.0,
            "hand_detected": False,
            "index_tip": None,
        }
        self._hands = None

        if self.available:
            self._hands = mp.solutions.hands.Hands(
                static_image_mode=False,
                max_num_hands=1,
                model_complexity=0,
                min_detection_confidence=0.7,
                min_tracking_confidence=0.7,
            )

    def close(self):
        if self._hands:
            self._hands.close()

    def _is_finger_extended(self, landmarks, tip_idx, pip_idx):
        return landmarks[tip_idx].y < landmarks[pip_idx].y

    def _is_thumb_extended(self, landmarks):
        # Heurística robusta simple: distancia pulgar al índice separada
        tip = landmarks[4]
        ip = landmarks[3]
        return abs(tip.x - ip.x) > 0.03 or abs(tip.y - ip.y) > 0.03

    def process(self, frame):
        now = time.time()
        if not self.available or self._hands is None:
            self._last_result = {
                "gesture_active": False,
                "tracking_confidence": 0.0,
                "hand_detected": False,
                "index_tip": None,
            }
            return self._last_result

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = self._hands.process(rgb)

        hand_detected = bool(result.multi_hand_landmarks)
        tracking_confidence = 0.0
        index_tip = None
        gun_pose = False

        if hand_detected:
            landmarks = result.multi_hand_landmarks[0].landmark
            if result.multi_handedness:
                tracking_confidence = float(result.multi_handedness[0].classification[0].score)

            index_extended = self._is_finger_extended(landmarks, 8, 6)
            middle_folded = not self._is_finger_extended(landmarks, 12, 10)
            ring_folded = not self._is_finger_extended(landmarks, 16, 14)
            pinky_folded = not self._is_finger_extended(landmarks, 20, 18)
            thumb_extended = self._is_thumb_extended(landmarks)

            gun_pose = all([index_extended, thumb_extended, middle_folded, ring_folded, pinky_folded])
            index_tip = (landmarks[8].x, landmarks[8].y)

        if now < self._cooldown_until:
            gesture_active = False
            self._gesture_started_at = None
        elif hand_detected and gun_pose and tracking_confidence >= 0.7:
            if self._gesture_started_at is None:
                self._gesture_started_at = now
            if (now - self._gesture_started_at) >= GESTURE_STABLE_SECONDS:
                gesture_active = True
                self._active_until = now
            else:
                gesture_active = False
        else:
            if (now - self._active_until) < 0.2:
                gesture_active = self._last_result["gesture_active"]
            else:
                gesture_active = False
                if self._last_result["gesture_active"]:
                    self._cooldown_until = now + GESTURE_COOLDOWN_SECONDS
            self._gesture_started_at = None

        self._last_result = {
            "gesture_active": gesture_active,
            "tracking_confidence": tracking_confidence,
            "hand_detected": hand_detected,
            "index_tip": index_tip,
        }
        return self._last_result


class AutoTracker:
    def __init__(self, feed):
        self.feed = feed
        self.last_command_ts = 0.0

    def _scaled_motor_step(self, delta, axis_step):
        scaled = int(round((delta / 0.5) * axis_step))
        if scaled == 0:
            return 0
        return max(-axis_step, min(axis_step, scaled))

    def update(self, index_tip):
        if index_tip is None:
            return
        now = time.time()
        if (now - self.last_command_ts) < TRACK_COMMAND_INTERVAL:
            return

        dx = index_tip[0] - 0.5
        dy = index_tip[1] - 0.5

        if abs(dx) <= TRACK_DEAD_ZONE and abs(dy) <= TRACK_DEAD_ZONE:
            return

        # Referencia directa al esquema del código aportado:
        # tapo.moveMotor(PAN_STEP, 0) / tapo.moveMotor(0, TILT_STEP)
        x_step = self._scaled_motor_step(dx, PAN_STEP)
        y_step = self._scaled_motor_step(-dy, TILT_STEP)

        if abs(x_step) <= TRACK_MAX_STEP:
            x_step = 0
        if abs(y_step) <= TRACK_MAX_STEP:
            y_step = 0

        if x_step == 0 and y_step == 0:
            return

        try:
            self.feed.move(x_step, y_step)
        except Exception:
            return
        self.last_command_ts = now


class VideoRecorder:
    def __init__(self, feed):
        self.feed = feed
        self.out = None
        self.recording = False
        self.started_at = 0.0
        self.last_write = 0.0
        self.write_interval = 1 / RECORD_FPS

    def _new_writer(self, frame):
        h, w, _ = frame.shape
        output_dir = self.feed._get_media_output_dir()
        filename = output_dir / self.feed._build_media_filename("auto", "mp4")
        writer = cv2.VideoWriter(
            str(filename),
            cv2.VideoWriter_fourcc(*"mp4v"),
            min(RECORD_FPS, self.feed.stream_fps or RECORD_FPS),
            (w, h),
        )
        return writer if writer.isOpened() else None

    def start(self, frame):
        self.stop()
        writer = self._new_writer(frame)
        if writer is None:
            return False
        self.out = writer
        self.recording = True
        self.started_at = time.time()
        self.last_write = 0.0
        return True

    def stop(self):
        if self.out is not None:
            self.out.release()
        self.out = None
        self.recording = False
        self.started_at = 0.0

    def write(self, frame):
        if not self.recording or self.out is None:
            return
        now = time.time()
        if (now - self.last_write) >= self.write_interval:
            self.out.write(frame)
            self.last_write = now

    def should_rotate(self):
        return self.recording and (time.time() - self.started_at) >= AUTO_RECORD_SECONDS


def _decode_if_needed(value: str) -> str:
    """Mantiene credenciales/tokens tal cual fueron ingresados."""
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
    def __init__(self, mac, usuario, password, tag="", settings=None):
        super().__init__(daemon=True, name=f"CameraStream-{mac}")
        self.mac = mac
        self.tag = tag

        # Guardamos versiones sin codificar para persistencia
        self.usuario_raw = _decode_if_needed(usuario)
        self.password_raw = _decode_if_needed(password)

        # Enviar credenciales RTSP con caracteres especiales tal cual (sin URL-encoding).
        self.usuario = self.usuario_raw
        self.password = self.password_raw
        self.ip = None
        self.rtsp_url = None
        self.frame = None
        self.stream_fps = RECORD_FPS

        self.capture_lock = threading.Lock()
        self.writer_lock = threading.Lock()
        self.state_lock = threading.Lock()

        self.recording = False
        self.out = None
        self.last_write = 0
        self.write_interval = 1 / RECORD_FPS

        self.state = {
            "gesture_active": False,
            "tracking_active": False,
            "recording_active": False,
            "last_trigger_time": 0.0,
        }

        self.gesture_detector = GestureDetector()
        self.auto_tracker = AutoTracker(self)
        self.video_recorder = VideoRecorder(self)

        self._frame_counter = 0
        self._last_gesture_process_ts = 0.0
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
        self.gesture_detector.close()
        with self.writer_lock:
            if self.out is not None:
                self.out.release()
                self.out = None
                self.recording = False
            self.video_recorder.stop()

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

    def _update_state(self, **kwargs):
        with self.state_lock:
            self.state.update(kwargs)

    def get_state(self):
        with self.state_lock:
            return dict(self.state)

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

            fps = cap.get(cv2.CAP_PROP_FPS)
            if fps and fps > 0:
                self.stream_fps = min(max(int(fps), 10), 20)

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

                frame = cv2.resize(frame, (640, 480), interpolation=cv2.INTER_AREA)
                with self.capture_lock:
                    self.frame = frame

                self._last_ok_read = time.time()
                self.connected = True
                self._write_if_recording(frame)
                self._process_auto_modes(frame)

            with self.writer_lock:
                if self.video_recorder.recording:
                    self.video_recorder.stop()
            self._update_state(gesture_active=False, tracking_active=False, recording_active=False)
            cap.release()
            self._force_reconnect_event.clear()
            time.sleep(1)

    def _process_auto_modes(self, frame):
        self._frame_counter += 1
        now = time.time()
        should_process = (
            self._frame_counter % GESTURE_FRAME_SKIP == 0
            and (now - self._last_gesture_process_ts) >= GESTURE_PROCESS_INTERVAL
        )

        if not should_process:
            if self.video_recorder.recording:
                self.video_recorder.write(frame)
            return

        self._last_gesture_process_ts = now
        result = self.gesture_detector.process(frame)
        gesture_active = result["gesture_active"]

        if gesture_active:
            self._update_state(gesture_active=True, tracking_active=True, last_trigger_time=now)
            self.auto_tracker.update(result["index_tip"])
            with self.writer_lock:
                if not self.video_recorder.recording:
                    self.video_recorder.start(frame)
                else:
                    self.video_recorder.write(frame)
                if self.video_recorder.should_rotate():
                    self.video_recorder.stop()
                    self.video_recorder.start(frame)
                self._update_state(recording_active=self.video_recorder.recording)
        else:
            with self.writer_lock:
                if self.video_recorder.recording:
                    self.video_recorder.write(frame)
                    self.video_recorder.stop()
            self._update_state(gesture_active=False, tracking_active=False, recording_active=False)

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

        # Igual que el código de referencia: Tapo(IP, EMAIL, PASSWORD)
        tapo_user = str(self.settings.get("tapo_user", ""))
        tapo_password = str(self.settings.get("tapo_password", ""))

        if not tapo_user or not tapo_password:
            raise RuntimeError(
                "Configura en la pestaña 'Configuración' el Usuario/email y Password de Tapo App"
            )

        return Tapo(self.ip, tapo_user, tapo_password)

    def _call_first_available(self, client, method_names, *args):
        for method_name in method_names:
            method = getattr(client, method_name, None)
            if callable(method):
                return method(*args)
        raise AttributeError(f"Ningún método disponible entre: {', '.join(method_names)}")

    def move(self, x_axis, y_axis):
        client = self.get_tapo_client()
        # Igual que el código de referencia:
        # tapo.moveMotor(0, TILT_STEP), tapo.moveMotor(PAN_STEP, 0)
        client.moveMotor(x_axis, y_axis)

    def zoom(self, zoom_in):
        client = self.get_tapo_client()
        if zoom_in:
            self._call_first_available(client, ["zoomIn", "zoom_in"])
        else:
            self._call_first_available(client, ["zoomOut", "zoom_out"])

    def move_to_coordinates(self, pan, tilt):
        client = self.get_tapo_client()
        self._call_first_available(client, ["pan_tilt_to", "panTiltTo"], pan, tilt)


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
            state = self.feed.get_state()
            badges = []
            if state["gesture_active"]:
                badges.append("🟢 GESTO ACTIVO")
            if state["tracking_active"]:
                badges.append("🎯 SIGUIENDO MANO")
            if state["recording_active"] or self.feed.recording:
                badges.append("🔴 GRABANDO")
            suffix = f" | {' | '.join(badges)}" if badges else ""
            self.status.setText(f"🟢 En línea | IP: {self.feed.ip or 'resolviendo'}{suffix}")
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

        self.btn_up.clicked.connect(lambda: self.send_move(0, TILT_STEP))
        self.btn_down.clicked.connect(lambda: self.send_move(0, -TILT_STEP))
        self.btn_left.clicked.connect(lambda: self.send_move(-PAN_STEP, 0))
        self.btn_right.clicked.connect(lambda: self.send_move(PAN_STEP, 0))
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
            "tag": w.feed.tag,
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
                feed = CameraFeed(
                    cam["mac"],
                    cam["usuario"],
                    cam["password"],
                    tag=cam.get("tag", ""),
                    settings=settings,
                )
                feed.start()
                widget = CameraWidget(feed)
                widgets.append(widget)
    except FileNotFoundError:
        pass
    return widgets
