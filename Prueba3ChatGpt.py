import sys
import cv2
import time
import threading
import subprocess
import re
from urllib.parse import quote

from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton,
    QVBoxLayout, QGridLayout, QHBoxLayout, QMainWindow
)
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import Qt, QTimer


# ================= CONFIG =================
CAMERAS = [
    {
        "mac": "CC:BA:BD:22:C0:4D",
        "usuario": "cepy_2026",
        "password": "Castelar2026"
    },
]

RED_BASE = "192.168.60."
# =========================================


# -------- BUSCAR IP POR MAC (WINDOWS) --------
def buscar_ip_por_mac(mac):
    mac = mac.lower().replace(":", "-")
    print(f"[*] Buscando IP para MAC {mac}")

    for i in range(1, 255):
        ip = f"{RED_BASE}{i}"
        subprocess.call(
            f"ping -n 1 -w 80 {ip}",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=True
        )

        salida = subprocess.check_output(
            "arp -a",
            shell=True
        ).decode("cp1252", errors="ignore")

        for linea in salida.splitlines():
            if mac in linea.lower():
                encontrada = re.findall(r"\d+\.\d+\.\d+\.\d+", linea)
                if encontrada:
                    print(f"[+] IP encontrada ({mac}): {encontrada[0]}")
                    return encontrada[0]

    print(f"[-] No se encontró IP para {mac}")
    return None


# -------- THREAD DE CÁMARA --------
class CameraFeed(threading.Thread):
    def __init__(self, mac, usuario, password):
        super().__init__(daemon=True)
        self.mac = mac
        self.ip = buscar_ip_por_mac(mac)

        self.usuario = quote(usuario, safe="")
        self.password = quote(password, safe="")

        if self.ip:
            self.rtsp_url = (
                f"rtsp://{self.usuario}:{self.password}@{self.ip}:554/stream1"
                "?rtsp_transport=tcp"
            )
        else:
            self.rtsp_url = None

        self.frame = None
        self.cap = None
        self.recording = False
        self.out = None

    def run(self):
        if not self.rtsp_url:
            return

        self.cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
        if not self.cap.isOpened():
            print(f"[-] No se pudo abrir RTSP {self.ip}")
            return

        while True:
            ret, frame = self.cap.read()
            if ret:
                self.frame = frame
                if self.recording and self.out:
                    self.out.write(frame)
            else:
                time.sleep(0.1)

    def capture(self):
        if self.frame is not None:
            name = f"captura_{self.ip}_{int(time.time())}.jpg"
            cv2.imwrite(name, self.frame)
            print(f"[+] Imagen guardada: {name}")

    def toggle_record(self):
        if not self.recording:
            if self.frame is None:
                print("[-] No hay frame disponible todavía para grabar")
                return

            h, w, _ = self.frame.shape
            fourcc = cv2.VideoWriter_fourcc(*"XVID")
            self.out = cv2.VideoWriter(
                f"grabacion_{self.ip}_{int(time.time())}.avi",
                fourcc, 20.0, (w, h)
            )
            if not self.out.isOpened():
                print(f"[-] No se pudo iniciar la grabación para {self.ip}")
                self.out = None
                return

            self.recording = True
            print(f"[+] Grabando {self.ip}")

        else:
            self.recording = False
            if self.out:
                self.out.release()
                self.out = None
            print(f"[+] Grabación detenida {self.ip}")


# -------- WIDGET DE CÁMARA --------
class CameraWidget(QWidget):
    def __init__(self, feed, main):
        super().__init__()
        self.feed = feed
        self.main = main

        self.label = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        self.label.mousePressEvent = self.expand

        self.btn_capture = QPushButton("📸 Capturar")
        self.btn_record = QPushButton("⏺️ Grabar")
        self.btn_back = QPushButton("🔙 Volver")

        self.btn_capture.clicked.connect(self.feed.capture)
        self.btn_record.clicked.connect(self.feed.toggle_record)
        self.btn_back.clicked.connect(self.main.show_general_view)

        buttons = QHBoxLayout()
        buttons.addWidget(self.btn_capture)
        buttons.addWidget(self.btn_record)
        buttons.addWidget(self.btn_back)

        self.layout = QVBoxLayout(self)
        self.layout.addWidget(self.label)
        self.layout.addLayout(buttons)

        self.show_buttons(False)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)

    def update_frame(self):
        if self.feed.frame is not None:
            rgb = cv2.cvtColor(self.feed.frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            img = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
            self.label.setPixmap(QPixmap.fromImage(img).scaled(
                self.label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))

    def expand(self, event):
        self.main.show_expanded_view(self)

    def show_buttons(self, show):
        self.btn_capture.setVisible(show)
        self.btn_record.setVisible(show)
        self.btn_back.setVisible(show)


# -------- MAIN WINDOW --------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tapo MultiCam (MAC → IP)")
        self.central = QWidget()
        self.setCentralWidget(self.central)

        self.grid = QGridLayout(self.central)
        self.widgets = []

        for cam in CAMERAS:
            feed = CameraFeed(cam["mac"], cam["usuario"], cam["password"])
            feed.start()
            widget = CameraWidget(feed, self)
            self.widgets.append(widget)

        self.show_general_view()

    def clear(self):
        while self.grid.count():
            self.grid.itemAt(0).widget().setParent(None)

    def show_general_view(self):
        self.clear()
        for w in self.widgets:
            w.show_buttons(False)

        cols = 2 if len(self.widgets) > 1 else 1
        r = c = 0
        for w in self.widgets:
            self.grid.addWidget(w, r, c)
            c += 1
            if c >= cols:
                c = 0
                r += 1

    def show_expanded_view(self, widget):
        self.clear()
        self.grid.addWidget(widget, 0, 0)
        widget.show_buttons(True)


# -------- MAIN --------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.showMaximized()
    sys.exit(app.exec())
