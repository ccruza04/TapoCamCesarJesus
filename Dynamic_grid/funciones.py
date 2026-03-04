"""Módulo de utilidades de cámaras.

Este archivo concentra la lógica de:
- conexión RTSP de cada cámara,
- captura de foto y grabación de video,
- controles PTZ (si `pytapo` está disponible),
- persistencia de configuración y listado de cámaras.
"""

from __future__ import annotations

import json
import re
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, unquote

import cv2
from PyQt6.QtCore import QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

try:
    from pytapo import Tapo
except ModuleNotFoundError:
    Tapo = None

RED_BASE = "192.168.60."
TIEMPO_PING_MS = 400
FPS_GRABACION = 15
INTERVALO_VERIFICACION_MS = 60_000
ARCHIVO_CONFIGURACION = "settings.json"
ARCHIVO_CAMARAS = "cameras.dat"


def decodificar_si_corresponde(valor: str) -> str:
    """Devuelve una cadena decodificada en URL si aplica."""
    try:
        return unquote(valor)
    except Exception:
        return valor


def buscar_ip_por_mac(mac: str) -> str | None:
    """Busca la IP de una MAC usando `ping` y `arp` (en entorno Windows)."""
    mac_normalizada = mac.lower().replace(":", "-")
    for host in range(1, 255):
        ip = f"{RED_BASE}{host}"
        subprocess.call(
            f"ping -n 1 -w {TIEMPO_PING_MS} {ip}",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=True,
        )
        salida = subprocess.check_output("arp -a", shell=True).decode("cp1252", errors="ignore")
        for linea in salida.splitlines():
            if mac_normalizada in linea.lower():
                ips = re.findall(r"\d+\.\d+\.\d+\.\d+", linea)
                if ips:
                    return ips[0]
    return None


class HiloCamara(threading.Thread):
    """Gestiona la conexión de una cámara y mantiene el último frame en memoria."""

    def __init__(self, mac: str, usuario: str, password: str, etiqueta: str = "", ajustes: dict | None = None):
        super().__init__(daemon=True, name=f"Camara-{mac}")
        self.mac = mac
        self.etiqueta = etiqueta

        self.usuario_real = decodificar_si_corresponde(usuario)
        self.password_real = decodificar_si_corresponde(password)
        self.usuario_url = quote(self.usuario_real, safe="")
        self.password_url = quote(self.password_real, safe="")

        self.ip: str | None = None
        self.url_rtsp: str | None = None
        self.frame = None
        self.conectada = False

        self.ajustes = ajustes or {}
        self.bloqueo_frame = threading.Lock()
        self.bloqueo_video = threading.Lock()

        self.grabando = False
        self.video_salida = None
        self.ultima_escritura = 0.0
        self.intervalo_escritura = 1 / FPS_GRABACION

        self.evento_detener = threading.Event()
        self.evento_reconectar = threading.Event()
        self.ultimo_frame_ok = 0.0

    def run(self) -> None:
        self._bucle_conexion()

    def detener(self) -> None:
        self.evento_detener.set()
        self.evento_reconectar.set()
        with self.bloqueo_video:
            if self.video_salida is not None:
                self.video_salida.release()
                self.video_salida = None
            self.grabando = False

    def solicitar_reconexion(self) -> None:
        self.evento_reconectar.set()

    def comprobar_conexion(self) -> None:
        if self.evento_detener.is_set():
            return
        sin_frame = (time.time() - self.ultimo_frame_ok) > 10
        if not self.conectada or sin_frame:
            self.solicitar_reconexion()

    def _directorio_media(self) -> Path:
        ruta = str(self.ajustes.get("media_directory", "")).strip()
        carpeta = Path(ruta) if ruta else Path(__file__).resolve().parent
        carpeta.mkdir(parents=True, exist_ok=True)
        return carpeta

    def _nombre_archivo(self, prefijo: str, extension: str) -> str:
        identificador = (self.ip or self.mac or "camara").replace(":", "-")
        marca_tiempo = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{prefijo}_{identificador}_{marca_tiempo}.{extension}"

    def _actualizar_url_rtsp(self) -> None:
        if self.ip:
            self.url_rtsp = f"rtsp://{self.usuario_url}:{self.password_url}@{self.ip}:554/stream1"

    def _resolver_ip(self) -> None:
        if self.ip is None:
            self.ip = buscar_ip_por_mac(self.mac)
            self._actualizar_url_rtsp()

    def _bucle_conexion(self) -> None:
        while not self.evento_detener.is_set():
            self._resolver_ip()
            if not self.url_rtsp:
                self.conectada = False
                time.sleep(3)
                continue

            captura = cv2.VideoCapture(self.url_rtsp, cv2.CAP_FFMPEG)
            captura.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            if not captura.isOpened():
                self.conectada = False
                captura.release()
                time.sleep(2)
                continue

            self.conectada = True
            self.ultimo_frame_ok = time.time()
            self.evento_reconectar.clear()

            while not self.evento_detener.is_set():
                if self.evento_reconectar.is_set():
                    self.conectada = False
                    break

                ok, frame = captura.read()
                if not ok or frame is None or frame.size == 0:
                    self.conectada = False
                    time.sleep(0.4)
                    break

                with self.bloqueo_frame:
                    self.frame = frame

                self.ultimo_frame_ok = time.time()
                self.conectada = True
                self._escribir_video_si_corresponde(frame)

            captura.release()
            self.evento_reconectar.clear()
            time.sleep(1)

    def _escribir_video_si_corresponde(self, frame) -> None:
        with self.bloqueo_video:
            if self.grabando and self.video_salida:
                ahora = time.time()
                if ahora - self.ultima_escritura >= self.intervalo_escritura:
                    self.video_salida.write(frame)
                    self.ultima_escritura = ahora

    def alternar_grabacion(self) -> bool:
        with self.bloqueo_video:
            if not self.grabando and self.frame is not None:
                alto, ancho, _ = self.frame.shape
                destino = self._directorio_media() / self._nombre_archivo("video", "mp4")
                self.video_salida = cv2.VideoWriter(
                    str(destino),
                    cv2.VideoWriter_fourcc(*"mp4v"),
                    FPS_GRABACION,
                    (ancho, alto),
                )
                if not self.video_salida.isOpened():
                    self.video_salida = None
                    self.grabando = False
                    return False
                self.grabando = True
                self.ultima_escritura = time.time()
                return True

            self.grabando = False
            if self.video_salida:
                self.video_salida.release()
                self.video_salida = None
            return True

    def capturar_foto(self) -> tuple[bool, str]:
        with self.bloqueo_frame:
            if self.frame is None:
                return False, "Sin imagen disponible"
            imagen = self.frame.copy()

        ruta = self._directorio_media() / self._nombre_archivo("foto", "jpg")
        if not cv2.imwrite(str(ruta), imagen):
            return False, "No se pudo guardar la foto"
        return True, str(ruta)

    def actualizar_ajustes(self, ajustes: dict) -> None:
        self.ajustes = ajustes

    def _cliente_tapo(self):
        if Tapo is None:
            raise RuntimeError("Falta 'pytapo'. Instala con: pip install pytapo")
        if not self.ip:
            raise RuntimeError("La cámara aún no tiene IP")

        usuario = self.ajustes.get("tapo_user", "").strip() or self.usuario_real
        password = self.ajustes.get("tapo_password", "").strip() or self.password_real
        return Tapo(self.ip, usuario, password)

    def _ejecutar_metodo_disponible(self, cliente, metodos: list[str], *args):
        for nombre in metodos:
            metodo = getattr(cliente, nombre, None)
            if callable(metodo):
                return metodo(*args)
        raise AttributeError(f"No hay método disponible entre: {', '.join(metodos)}")

    def mover(self, eje_x: int, eje_y: int) -> None:
        cliente = self._cliente_tapo()
        self._ejecutar_metodo_disponible(cliente, ["moveMotor", "move_motor", "move"], eje_x, eje_y)

    def zoom(self, acercar: bool) -> None:
        cliente = self._cliente_tapo()
        if acercar:
            self._ejecutar_metodo_disponible(cliente, ["zoomIn", "zoom_in"])
        else:
            self._ejecutar_metodo_disponible(cliente, ["zoomOut", "zoom_out"])


class TarjetaCamara(QWidget):
    """Tarjeta compacta para la grilla principal."""

    def __init__(self, hilo: HiloCamara):
        super().__init__()
        self.hilo = hilo
        self.ventana_camara = None

        self.setObjectName("cameraCard")
        self.disposicion = QVBoxLayout(self)

        titulo = hilo.etiqueta or hilo.mac
        self.etiqueta_titulo = QLabel(f"📷 {titulo}")
        self.etiqueta_titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.etiqueta_video = QLabel("Cargando...")
        self.etiqueta_video.setObjectName("videoLabel")
        self.etiqueta_video.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.etiqueta_video.setMinimumSize(280, 180)

        self.etiqueta_estado = QLabel("Estado: Desconectada")
        self.etiqueta_estado.setObjectName("statusLabel")

        fila_botones = QHBoxLayout()
        self.btn_grabar = QPushButton("● Grabar")
        self.btn_foto = QPushButton("📸 Foto")
        self.btn_grabar.clicked.connect(self.alternar_grabacion)
        self.btn_foto.clicked.connect(self.capturar_foto)
        fila_botones.addWidget(self.btn_grabar)
        fila_botones.addWidget(self.btn_foto)

        self.disposicion.addWidget(self.etiqueta_titulo)
        self.disposicion.addWidget(self.etiqueta_video)
        self.disposicion.addWidget(self.etiqueta_estado)
        self.disposicion.addLayout(fila_botones)

        self.temporizador_frame = QTimer(self)
        self.temporizador_frame.timeout.connect(self.actualizar_frame)
        self.temporizador_frame.start(40)

        self.temporizador_conexion = QTimer(self)
        self.temporizador_conexion.timeout.connect(self.hilo.comprobar_conexion)
        self.temporizador_conexion.start(INTERVALO_VERIFICACION_MS)

    def alternar_grabacion(self) -> None:
        if self.hilo.alternar_grabacion():
            if self.hilo.grabando:
                self.btn_grabar.setText("■ Detener")
                self.etiqueta_estado.setText("Estado: Grabando")
            else:
                self.btn_grabar.setText("● Grabar")
                self.etiqueta_estado.setText("Estado: Vista previa")

    def capturar_foto(self) -> None:
        ok, mensaje = self.hilo.capturar_foto()
        self.etiqueta_estado.setText(f"Estado: {'Foto guardada' if ok else mensaje}")

    def actualizar_frame(self) -> None:
        with self.hilo.bloqueo_frame:
            frame = self.hilo.frame.copy() if self.hilo.frame is not None else None

        if frame is None:
            self.etiqueta_estado.setText("Estado: Desconectada")
            return

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        alto, ancho, canales = frame_rgb.shape
        imagen = QImage(frame_rgb.data, ancho, alto, canales * ancho, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(imagen).scaled(
            self.etiqueta_video.width(),
            self.etiqueta_video.height(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.etiqueta_video.setPixmap(pixmap)
        self.etiqueta_estado.setText("Estado: En línea")

    def mouseDoubleClickEvent(self, _event):  # noqa: N802
        if self.ventana_camara is None:
            self.ventana_camara = VentanaCamara(self.hilo)
        self.ventana_camara.show()
        self.ventana_camara.raise_()
        self.ventana_camara.activateWindow()


class VentanaCamara(QWidget):
    """Vista ampliada con controles básicos y PTZ."""

    senal_error = pyqtSignal(str)

    def __init__(self, hilo: HiloCamara):
        super().__init__()
        self.hilo = hilo
        self.setWindowTitle(f"Cámara: {hilo.etiqueta or hilo.mac}")
        self.resize(960, 620)

        self.etiqueta_video = QLabel("Cargando...")
        self.etiqueta_video.setObjectName("videoLabel")
        self.etiqueta_video.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.etiqueta_estado = QLabel("Estado: Inicializando")

        self.btn_grabar = QPushButton("● Grabar")
        self.btn_foto = QPushButton("📸 Foto")
        self.btn_grabar.clicked.connect(self.alternar_grabacion)
        self.btn_foto.clicked.connect(self.capturar_foto)

        fila_acciones = QHBoxLayout()
        fila_acciones.addWidget(self.btn_grabar)
        fila_acciones.addWidget(self.btn_foto)

        contenedor_ptz = QWidget()
        grilla_ptz = QGridLayout(contenedor_ptz)
        self.btn_arriba = QPushButton("↑")
        self.btn_abajo = QPushButton("↓")
        self.btn_izquierda = QPushButton("←")
        self.btn_derecha = QPushButton("→")
        self.btn_zoom_mas = QPushButton("+ Zoom")
        self.btn_zoom_menos = QPushButton("- Zoom")

        grilla_ptz.addWidget(self.btn_arriba, 0, 1)
        grilla_ptz.addWidget(self.btn_izquierda, 1, 0)
        grilla_ptz.addWidget(self.btn_derecha, 1, 2)
        grilla_ptz.addWidget(self.btn_abajo, 2, 1)
        grilla_ptz.addWidget(self.btn_zoom_mas, 1, 3)
        grilla_ptz.addWidget(self.btn_zoom_menos, 1, 4)

        self.btn_arriba.clicked.connect(lambda: self._accion_segura(lambda: self.hilo.mover(0, 1), "Movimiento enviado"))
        self.btn_abajo.clicked.connect(lambda: self._accion_segura(lambda: self.hilo.mover(0, -1), "Movimiento enviado"))
        self.btn_izquierda.clicked.connect(lambda: self._accion_segura(lambda: self.hilo.mover(-1, 0), "Movimiento enviado"))
        self.btn_derecha.clicked.connect(lambda: self._accion_segura(lambda: self.hilo.mover(1, 0), "Movimiento enviado"))
        self.btn_zoom_mas.clicked.connect(lambda: self._accion_segura(lambda: self.hilo.zoom(True), "Zoom + enviado"))
        self.btn_zoom_menos.clicked.connect(lambda: self._accion_segura(lambda: self.hilo.zoom(False), "Zoom - enviado"))

        self.senal_error.connect(lambda texto: self.etiqueta_estado.setText(f"Estado: {texto}"))

        layout = QVBoxLayout(self)
        layout.addWidget(self.etiqueta_video, stretch=1)
        layout.addWidget(self.etiqueta_estado)
        layout.addLayout(fila_acciones)
        layout.addWidget(contenedor_ptz)

        self.temporizador = QTimer(self)
        self.temporizador.timeout.connect(self.actualizar_frame)
        self.temporizador.start(40)

        self._habilitar_ptz(Tapo is not None)

    def _habilitar_ptz(self, habilitar: bool) -> None:
        for boton in [
            self.btn_arriba,
            self.btn_abajo,
            self.btn_izquierda,
            self.btn_derecha,
            self.btn_zoom_mas,
            self.btn_zoom_menos,
        ]:
            boton.setEnabled(habilitar)
        if not habilitar:
            self.etiqueta_estado.setText("Estado: PTZ deshabilitado (falta pytapo)")

    def _accion_segura(self, accion, mensaje_ok: str) -> None:
        try:
            accion()
            self.etiqueta_estado.setText(f"Estado: {mensaje_ok}")
        except Exception as exc:  # pragma: no cover - depende de red/dispositivo
            self.senal_error.emit(str(exc))

    def alternar_grabacion(self) -> None:
        if self.hilo.alternar_grabacion():
            self.btn_grabar.setText("■ Detener" if self.hilo.grabando else "● Grabar")

    def capturar_foto(self) -> None:
        ok, mensaje = self.hilo.capturar_foto()
        self.etiqueta_estado.setText(f"Estado: {'Foto guardada' if ok else mensaje}")

    def actualizar_frame(self) -> None:
        with self.hilo.bloqueo_frame:
            frame = self.hilo.frame.copy() if self.hilo.frame is not None else None

        if frame is None:
            return

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        alto, ancho, canales = frame_rgb.shape
        imagen = QImage(frame_rgb.data, ancho, alto, canales * ancho, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(imagen).scaled(
            self.etiqueta_video.width(),
            self.etiqueta_video.height(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.etiqueta_video.setPixmap(pixmap)


# Compatibilidad con nombres anteriores
CameraFeed = HiloCamara
CameraWidget = TarjetaCamara
CameraWindow = VentanaCamara


def guardar_ajustes(ajustes: dict) -> None:
    Path(ARCHIVO_CONFIGURACION).write_text(json.dumps(ajustes, indent=4, ensure_ascii=False), encoding="utf-8")


def update_settings(parcial: dict) -> dict:
    actuales = load_settings()
    actuales.update(parcial)
    guardar_ajustes(actuales)
    return actuales


def load_settings() -> dict:
    ruta = Path(ARCHIVO_CONFIGURACION)
    if not ruta.exists():
        return {"tapo_user": "", "tapo_password": "", "media_directory": ""}

    try:
        data = json.loads(ruta.read_text(encoding="utf-8"))
        return {
            "tapo_user": data.get("tapo_user", ""),
            "tapo_password": data.get("tapo_password", ""),
            "media_directory": data.get("media_directory", ""),
        }
    except Exception:
        return {"tapo_user": "", "tapo_password": "", "media_directory": ""}


def save_settings(settings: dict) -> None:
    guardar_ajustes(settings)


def save_cameras(tarjetas: list[TarjetaCamara]) -> None:
    camaras = []
    for tarjeta in tarjetas:
        camaras.append(
            {
                "mac": tarjeta.hilo.mac,
                "usuario": tarjeta.hilo.usuario_real,
                "password": tarjeta.hilo.password_real,
                "tag": tarjeta.hilo.etiqueta,
            }
        )
    Path(ARCHIVO_CAMARAS).write_text(json.dumps(camaras, indent=4, ensure_ascii=False), encoding="utf-8")


def load_cameras(settings: dict | None = None) -> list[TarjetaCamara]:
    ruta = Path(ARCHIVO_CAMARAS)
    if not ruta.exists():
        return []

    try:
        camaras = json.loads(ruta.read_text(encoding="utf-8"))
    except Exception:
        return []

    tarjetas: list[TarjetaCamara] = []
    for camara in camaras:
        hilo = HiloCamara(
            mac=camara.get("mac", ""),
            usuario=camara.get("usuario", ""),
            password=camara.get("password", ""),
            etiqueta=camara.get("tag", ""),
            ajustes=settings,
        )
        hilo.start()
        tarjetas.append(TarjetaCamara(hilo))
    return tarjetas
