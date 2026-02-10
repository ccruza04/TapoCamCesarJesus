import sys, cv2, time, threading, subprocess, re, random, json
from urllib.parse import quote
from PyQt6.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import Qt, QTimer

RED_BASE = "192.168.60."
RECORD_FPS = 15

# ---------------- BUSCAR IP ----------------
def buscar_ip_por_mac(mac):
    """Búsqueda rápida de IP por MAC usando ping de 1 intento"""
    mac = mac.lower().replace(":", "-")
    for i in range(1, 255):
        ip = f"{RED_BASE}{i}"
        subprocess.call(
            f"ping -n 1 -w 20 {ip}",  # 1 ping, timeout 20ms
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=True
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
        self.usuario = quote(usuario, safe="")
        self.password = quote(password, safe="")
        self.ip = None
        self.rtsp_url = None
        self.frame = None
        self.recording = False
        self.out = None
        self.last_write = 0
        self.write_interval = 1 / RECORD_FPS

        # hilo para buscar IP y arrancar el flujo
        threading.Thread(target=self.init_ip_and_rtsp, daemon=True).start()

    def init_ip_and_rtsp(self):
        """Busca IP y prepara RTSP"""
        self.ip = buscar_ip_por_mac(self.mac)
        if self.ip:
            self.rtsp_url = f"rtsp://{self.usuario}:{self.password}@{self.ip}:554/stream1"
            threading.Thread(target=self.run_capture, daemon=True).start()

    def run_capture(self):
        if not self.rtsp_url:
            return

        while True:
            cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            # cap.set(cv2.CAP_PROP_LOGLEVEL, 3)  # ❌ eliminar esta línea

            while True:
                ret, frame = cap.read()

                # Frame inválido → reconectar
                if not ret or frame is None or frame.size == 0:
                    cap.release()
                    time.sleep(1)  # esperar antes de reconectar
                    break  # salir del bucle interno para reconectar

                self.frame = frame

                # Grabación
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
                (w, h)
            )
            self.recording = True
        else:
            self.recording = False
            if self.out:
                self.out.release()
                self.out = None

# ---------------- CAMERA WIDGET ----------------
class CameraWidget(QWidget):
    def __init__(self, feed):
        super().__init__()
        self.feed = feed
        accent = random.choice(["#38BDF8", "#A7F3D0", "#FDE68A", "#FCA5A5"])

        self.setStyleSheet(f"""
        QWidget {{
            background-color: #111827;
            border-radius: 12px;
            border: 2px solid {accent};
        }}
        """)

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

        # doble click abre ventana independiente
        self.label.mouseDoubleClickEvent = self.open_window
        self.cam_window = None

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(40)

    def update_frame(self):
        if self.feed.frame is not None:
            rgb = cv2.cvtColor(self.feed.frame, cv2.COLOR_BGR2RGB)
            img = QImage(rgb.data, rgb.shape[1], rgb.shape[0],
                         rgb.strides[0], QImage.Format.Format_RGB888)
            self.label.setPixmap(QPixmap.fromImage(img).scaled(
                self.label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))

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
            rgb = cv2.cvtColor(self.feed.frame, cv2.COLOR_BGR2RGB)
            img = QImage(rgb.data, rgb.shape[1], rgb.shape[0],
                         rgb.strides[0], QImage.Format.Format_RGB888)
            self.label.setPixmap(QPixmap.fromImage(img).scaled(
                self.label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))

# ---------------- GUARDAR Y CARGAR ----------------
def save_cameras(widgets):
    cams_data = []
    for w in widgets:
        cam = {
            "mac": w.feed.mac,
            "usuario": w.feed.usuario,
            "password": w.feed.password
        }
        cams_data.append(cam)
    with open("cameras.dat", "w") as f:
        f.write(json.dumps(cams_data, indent=4))

def load_cameras():
    widgets = []
    try:
        with open("cameras.dat", "r") as f:
            cams_data = json.loads(f.read())
            for cam in cams_data:
                feed = CameraFeed(cam["mac"], cam["usuario"], cam["password"])
                widget = CameraWidget(feed)
                widgets.append(widget)
    except FileNotFoundError:
        pass
    return widgets
