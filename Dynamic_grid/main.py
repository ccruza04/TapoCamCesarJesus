"""Aplicación principal para monitoreo de cámaras Tapo."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import cv2
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QImage, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from estilos import ESTILO_APP
from funciones import HiloCamara, TarjetaCamara, load_cameras, load_settings, save_cameras, update_settings

EXT_IMAGEN = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp"}
EXT_VIDEO = {".mp4", ".avi", ".mov", ".mkv", ".wmv", ".webm", ".m4v"}


class PanelMedia(QWidget):
    """Explorador sencillo para fotos y videos guardados."""

    def __init__(self, directorio: str = "", parent=None):
        super().__init__(parent)
        self.directorio = directorio
        self.modo_seleccion = False

        self.lbl_ruta = QLabel("Directorio actual: -")
        self.lbl_ruta.setWordWrap(True)

        self.lista = QListWidget()
        self.lista.itemDoubleClicked.connect(self.abrir_item)
        self.lista.currentItemChanged.connect(self.actualizar_preview)

        self.lbl_preview = QLabel("Selecciona un archivo para previsualizar")
        self.lbl_preview.setObjectName("videoLabel")
        self.lbl_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_preview.setMinimumHeight(240)

        self.lbl_info = QLabel("")
        self.lbl_info.setWordWrap(True)

        btn_refrescar = QPushButton("Refrescar")
        btn_refrescar.clicked.connect(self.cargar_media)

        btn_borrar = QPushButton("Borrar")
        btn_borrar.clicked.connect(self.borrar_item_actual)

        self.chk_seleccion = QCheckBox("Modo selección")
        self.chk_seleccion.stateChanged.connect(self.cambiar_modo_seleccion)

        self.btn_borrar_todo = QPushButton("Borrar seleccionados")
        self.btn_borrar_todo.setObjectName("primaryButton")
        self.btn_borrar_todo.clicked.connect(self.borrar_seleccionados)
        self.btn_borrar_todo.hide()

        fila = QHBoxLayout()
        fila.addWidget(btn_refrescar)
        fila.addWidget(btn_borrar)
        fila.addStretch()
        fila.addWidget(self.chk_seleccion)
        fila.addWidget(self.btn_borrar_todo)

        layout = QVBoxLayout(self)
        layout.addWidget(self.lbl_ruta)
        layout.addLayout(fila)
        layout.addWidget(self.lista)
        layout.addWidget(self.lbl_preview)
        layout.addWidget(self.lbl_info)

        self.establecer_directorio(directorio)

    def establecer_directorio(self, directorio: str) -> None:
        self.directorio = directorio
        self.cargar_media()

    def _archivos_media(self):
        if not self.directorio:
            return []
        base = Path(self.directorio)
        if not base.exists() or not base.is_dir():
            return []
        return sorted(
            [p for p in base.iterdir() if p.is_file() and p.suffix.lower() in (EXT_IMAGEN | EXT_VIDEO)],
            key=lambda x: x.name.lower(),
        )

    def cargar_media(self) -> None:
        self.lista.clear()
        self.lbl_preview.setText("Selecciona un archivo para previsualizar")
        self.lbl_preview.setPixmap(QPixmap())
        self.lbl_info.setText("")
        self.lbl_ruta.setText(f"Directorio actual: {self.directorio or 'No definido'}")

        for archivo in self._archivos_media():
            item = QListWidgetItem(archivo.name)
            item.setData(Qt.ItemDataRole.UserRole, str(archivo))
            if self.modo_seleccion:
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Unchecked)
            self.lista.addItem(item)

    def abrir_item(self, item: QListWidgetItem) -> None:
        ruta = item.data(Qt.ItemDataRole.UserRole)
        if ruta:
            QDesktopServices.openUrl(QUrl.fromLocalFile(ruta))

    def actualizar_preview(self, actual: QListWidgetItem | None, _anterior) -> None:
        if not actual:
            return
        ruta = Path(actual.data(Qt.ItemDataRole.UserRole))
        self.lbl_info.setText(f"Archivo: {ruta.name}\nTamaño: {ruta.stat().st_size / 1024:.1f} KB")

        if ruta.suffix.lower() in EXT_IMAGEN:
            pixmap = QPixmap(str(ruta)).scaled(
                self.lbl_preview.width() or 600,
                self.lbl_preview.height() or 240,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.lbl_preview.setPixmap(pixmap)
            return

        if ruta.suffix.lower() in EXT_VIDEO:
            captura = cv2.VideoCapture(str(ruta))
            ok, frame = captura.read()
            captura.release()
            if ok and frame is not None:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                alto, ancho, canales = rgb.shape
                img = QImage(rgb.data, ancho, alto, canales * ancho, QImage.Format.Format_RGB888)
                pixmap = QPixmap.fromImage(img).scaled(
                    self.lbl_preview.width() or 600,
                    self.lbl_preview.height() or 240,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self.lbl_preview.setPixmap(pixmap)
                return

        self.lbl_preview.setText("Sin previsualización disponible")

    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        self.actualizar_preview(self.lista.currentItem(), None)

    def borrar_item_actual(self) -> None:
        item = self.lista.currentItem()
        if not item:
            return
        ruta = Path(item.data(Qt.ItemDataRole.UserRole))
        ruta.unlink(missing_ok=True)
        self.cargar_media()

    def cambiar_modo_seleccion(self, estado: int) -> None:
        self.modo_seleccion = estado == int(Qt.CheckState.Checked)
        self.btn_borrar_todo.setVisible(self.modo_seleccion)
        self.cargar_media()

    def borrar_seleccionados(self) -> None:
        for i in range(self.lista.count()):
            item = self.lista.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                Path(item.data(Qt.ItemDataRole.UserRole)).unlink(missing_ok=True)
        self.cargar_media()


class DialogoCamara(QDialog):
    """Formulario para alta/edición de cámara."""

    def __init__(self, parent=None, titulo="Agregar cámara", texto_boton="Guardar", valores=None):
        super().__init__(parent)
        self.setWindowTitle(titulo)
        self.setModal(True)

        valores = valores or {}
        self.inp_mac = QLineEdit(valores.get("mac", ""))
        self.inp_usuario = QLineEdit(valores.get("usuario", ""))
        self.inp_password = QLineEdit(valores.get("password", ""))
        self.inp_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.inp_tag = QLineEdit(valores.get("tag", ""))

        form = QFormLayout()
        form.addRow("MAC:", self.inp_mac)
        form.addRow("Usuario:", self.inp_usuario)
        form.addRow("Contraseña:", self.inp_password)
        form.addRow("Etiqueta:", self.inp_tag)

        btn_guardar = QPushButton(texto_boton)
        btn_guardar.setObjectName("primaryButton")
        btn_cancelar = QPushButton("Cancelar")
        btn_guardar.clicked.connect(self.accept)
        btn_cancelar.clicked.connect(self.reject)

        fila = QHBoxLayout()
        fila.addWidget(btn_guardar)
        fila.addWidget(btn_cancelar)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(fila)

    def valores(self) -> dict:
        return {
            "mac": self.inp_mac.text().strip(),
            "usuario": self.inp_usuario.text().strip(),
            "password": self.inp_password.text().strip(),
            "tag": self.inp_tag.text().strip(),
        }


class PanelListadoCamaras(QWidget):
    """Tabla de cámaras con filtros básicos."""

    def __init__(self, parent=None, al_editar=None, al_borrar=None):
        super().__init__(parent)
        self.tarjetas = []
        self.al_editar = al_editar
        self.al_borrar = al_borrar

        self.inp_filtro = QLineEdit()
        self.inp_filtro.setPlaceholderText("Filtrar por MAC o etiqueta")
        self.inp_filtro.textChanged.connect(self.recargar)

        self.tabla = QTableWidget(0, 6)
        self.tabla.setHorizontalHeaderLabels(["Etiqueta", "MAC", "IP", "Estado", "Editar", "Borrar"])

        layout = QVBoxLayout(self)
        layout.addWidget(self.inp_filtro)
        layout.addWidget(self.tabla)

    def set_tarjetas(self, tarjetas) -> None:
        self.tarjetas = list(tarjetas)
        self.recargar()

    def recargar(self) -> None:
        texto = self.inp_filtro.text().strip().lower()
        visibles = [
            t
            for t in self.tarjetas
            if not texto or texto in t.hilo.mac.lower() or texto in (t.hilo.etiqueta or "").lower()
        ]

        self.tabla.setRowCount(len(visibles))
        for fila, tarjeta in enumerate(visibles):
            hilo = tarjeta.hilo
            estado = "En línea" if hilo.conectada else "Desconectada"
            self.tabla.setItem(fila, 0, QTableWidgetItem(hilo.etiqueta or "-"))
            self.tabla.setItem(fila, 1, QTableWidgetItem(hilo.mac))
            self.tabla.setItem(fila, 2, QTableWidgetItem(hilo.ip or "-"))
            self.tabla.setItem(fila, 3, QTableWidgetItem(estado))

            btn_editar = QPushButton("Editar")
            btn_borrar = QPushButton("Borrar")
            btn_editar.clicked.connect(lambda _=None, t=tarjeta: self.al_editar and self.al_editar(t))
            btn_borrar.clicked.connect(lambda _=None, t=tarjeta: self.al_borrar and self.al_borrar(t))
            self.tabla.setCellWidget(fila, 4, btn_editar)
            self.tabla.setCellWidget(fila, 5, btn_borrar)


class VentanaPrincipal(QMainWindow):
    """Ventana principal de la aplicación."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gestor CCTV Tapo")
        self.resize(1250, 780)

        self.ajustes = load_settings()
        self.tarjetas = load_cameras(self.ajustes)
        self.ventana_media = None

        contenedor = QWidget()
        self.setCentralWidget(contenedor)
        raiz = QVBoxLayout(contenedor)

        encabezado = QHBoxLayout()
        self.lbl_titulo = QLabel("Panel de cámaras")
        self.lbl_titulo.setObjectName("headerTitle")
        self.lbl_contador = QLabel("")
        self.lbl_contador.setObjectName("headerCounter")

        btn_agregar = QPushButton("➕ Agregar cámara")
        btn_agregar.setObjectName("primaryButton")
        btn_agregar.clicked.connect(self.dialogo_agregar)

        btn_galeria = QPushButton("🖼 Abrir galería")
        btn_galeria.clicked.connect(self.abrir_ventana_media)

        encabezado.addWidget(self.lbl_titulo)
        encabezado.addStretch()
        encabezado.addWidget(self.lbl_contador)
        encabezado.addWidget(btn_agregar)
        encabezado.addWidget(btn_galeria)

        self.pestanas = QTabWidget()
        self._crear_tab_camaras()
        self._crear_tab_ajustes()
        self._crear_tab_media()
        self._crear_tab_listado()

        raiz.addLayout(encabezado)
        raiz.addWidget(self.pestanas)

        self._reconstruir_grilla()

    def _crear_tab_camaras(self) -> None:
        self.tab_camaras = QWidget()
        self.grilla_camaras = QGridLayout(self.tab_camaras)
        self.pestanas.addTab(self.tab_camaras, "Cámaras")

    def _crear_tab_ajustes(self) -> None:
        tab = QWidget()
        form = QFormLayout(tab)

        self.inp_tapo_usuario = QLineEdit(self.ajustes.get("tapo_user", ""))
        self.inp_tapo_password = QLineEdit(self.ajustes.get("tapo_password", ""))
        self.inp_tapo_password.setEchoMode(QLineEdit.EchoMode.Password)

        self.inp_ruta_media = QLineEdit(self.ajustes.get("media_directory", ""))
        btn_buscar = QPushButton("Buscar")
        btn_buscar.clicked.connect(self.seleccionar_carpeta_media)

        fila_ruta = QHBoxLayout()
        fila_ruta.addWidget(self.inp_ruta_media)
        fila_ruta.addWidget(btn_buscar)

        btn_guardar = QPushButton("Guardar ajustes")
        btn_guardar.setObjectName("primaryButton")
        btn_guardar.clicked.connect(self.guardar_ajustes)

        form.addRow("Usuario Tapo:", self.inp_tapo_usuario)
        form.addRow("Contraseña Tapo:", self.inp_tapo_password)
        form.addRow("Carpeta de fotos/videos:", fila_ruta)
        form.addRow(btn_guardar)

        self.pestanas.addTab(tab, "Ajustes")

    def _crear_tab_media(self) -> None:
        self.panel_media = PanelMedia(self.ajustes.get("media_directory", ""))
        self.pestanas.addTab(self.panel_media, "Galería")

    def _crear_tab_listado(self) -> None:
        self.panel_listado = PanelListadoCamaras(
            al_editar=self.dialogo_editar,
            al_borrar=self.borrar_con_confirmacion,
        )
        self.pestanas.addTab(self.panel_listado, "Listado")

    def _reconstruir_grilla(self) -> None:
        while self.grilla_camaras.count():
            item = self.grilla_camaras.takeAt(0)
            if item and item.widget():
                item.widget().setParent(None)

        if not self.tarjetas:
            vacio = QLabel("No hay cámaras cargadas. Usa 'Agregar cámara'.")
            vacio.setObjectName("emptyState")
            vacio.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.grilla_camaras.addWidget(vacio, 0, 0)
        else:
            columnas = max(1, math.floor(self.width() / 390))
            for i, tarjeta in enumerate(self.tarjetas):
                self.grilla_camaras.addWidget(tarjeta, i // columnas, i % columnas)

        self.lbl_contador.setText(f"{len(self.tarjetas)} cámaras")
        self.panel_listado.set_tarjetas(self.tarjetas)
        save_cameras(self.tarjetas)

    def dialogo_agregar(self) -> None:
        dialogo = DialogoCamara(self)
        if dialogo.exec() != QDialog.DialogCode.Accepted:
            return

        data = dialogo.valores()
        if not data["mac"] or not data["usuario"] or not data["password"]:
            QMessageBox.warning(self, "Validación", "MAC, usuario y contraseña son obligatorios")
            return

        hilo = HiloCamara(data["mac"], data["usuario"], data["password"], data["tag"], self.ajustes)
        hilo.start()
        self.tarjetas.append(TarjetaCamara(hilo))
        self._reconstruir_grilla()

    def dialogo_editar(self, tarjeta: TarjetaCamara) -> None:
        datos = {
            "mac": tarjeta.hilo.mac,
            "usuario": tarjeta.hilo.usuario_real,
            "password": tarjeta.hilo.password_real,
            "tag": tarjeta.hilo.etiqueta,
        }
        dialogo = DialogoCamara(self, titulo="Editar cámara", texto_boton="Actualizar", valores=datos)
        if dialogo.exec() != QDialog.DialogCode.Accepted:
            return

        nuevos = dialogo.valores()
        if not nuevos["mac"] or not nuevos["usuario"] or not nuevos["password"]:
            QMessageBox.warning(self, "Validación", "MAC, usuario y contraseña son obligatorios")
            return

        indice = self.tarjetas.index(tarjeta)
        tarjeta.hilo.detener()
        tarjeta.deleteLater()

        hilo = HiloCamara(nuevos["mac"], nuevos["usuario"], nuevos["password"], nuevos["tag"], self.ajustes)
        hilo.start()
        self.tarjetas[indice] = TarjetaCamara(hilo)
        self._reconstruir_grilla()

    def borrar_con_confirmacion(self, tarjeta: TarjetaCamara) -> None:
        respuesta = QMessageBox.question(
            self,
            "Confirmar",
            f"¿Borrar cámara {tarjeta.hilo.mac}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if respuesta != QMessageBox.StandardButton.Yes:
            return

        tarjeta.hilo.detener()
        self.tarjetas.remove(tarjeta)
        tarjeta.deleteLater()
        self._reconstruir_grilla()

    def seleccionar_carpeta_media(self) -> None:
        ruta = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta")
        if ruta:
            self.inp_ruta_media.setText(ruta)

    def guardar_ajustes(self) -> None:
        self.ajustes = update_settings(
            {
                "tapo_user": self.inp_tapo_usuario.text().strip(),
                "tapo_password": self.inp_tapo_password.text().strip(),
                "media_directory": self.inp_ruta_media.text().strip(),
            }
        )
        for tarjeta in self.tarjetas:
            tarjeta.hilo.actualizar_ajustes(self.ajustes)

        self.panel_media.establecer_directorio(self.ajustes.get("media_directory", ""))
        self.statusBar().showMessage("Ajustes guardados", 3000)

    def abrir_ventana_media(self) -> None:
        directorio = self.ajustes.get("media_directory", "")
        if self.ventana_media is None:
            self.ventana_media = PanelMedia(directorio)
            self.ventana_media.setWindowTitle("Galería de media")
            self.ventana_media.resize(900, 580)
        else:
            self.ventana_media.establecer_directorio(directorio)
        self.ventana_media.show()
        self.ventana_media.raise_()
        self.ventana_media.activateWindow()

    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        self._reconstruir_grilla()

    def closeEvent(self, event):  # noqa: N802
        for tarjeta in self.tarjetas:
            tarjeta.hilo.detener()
        super().closeEvent(event)


# Compatibilidad de nombre previo
MainWindow = VentanaPrincipal

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(ESTILO_APP)
    ventana = VentanaPrincipal()
    ventana.show()
    sys.exit(app.exec())
