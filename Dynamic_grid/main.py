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
    QGroupBox,
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

from estilos import APP_STYLE
from funciones import CameraFeed, CameraWidget, load_cameras, load_settings, save_cameras, update_settings


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".wmv", ".webm", ".m4v"}


class MediaPanel(QWidget):
    def __init__(self, directory="", parent=None):
        super().__init__(parent)
        self.directory = directory
        self.selection_mode = False

        self.path_label = QLabel("Directorio actual: -")
        self.path_label.setWordWrap(True)

        self.media_list = QListWidget()
        self.media_list.itemDoubleClicked.connect(self.open_item)
        self.media_list.currentItemChanged.connect(self.update_preview)

        self.preview_label = QLabel("Selecciona un archivo para previsualizar")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumHeight(240)
        self.preview_label.setObjectName("videoLabel")

        self.preview_info = QLabel("")
        self.preview_info.setWordWrap(True)

        self.btn_refresh = QPushButton("Refrescar")
        self.btn_refresh.clicked.connect(self.load_media)

        self.btn_delete = QPushButton("Borrar")
        self.btn_delete.clicked.connect(self.delete_selected_item)

        self.selection_checkbox = QCheckBox("Modo selección")
        self.selection_checkbox.stateChanged.connect(self.toggle_selection_mode)

        self.btn_delete_all = QPushButton("Borrar Todo")
        self.btn_delete_all.setObjectName("primaryButton")
        self.btn_delete_all.clicked.connect(self.delete_checked_items)
        self.btn_delete_all.hide()

        actions = QHBoxLayout()
        actions.addWidget(self.btn_refresh)
        actions.addWidget(self.btn_delete)
        actions.addStretch()
        actions.addWidget(self.selection_checkbox)
        actions.addWidget(self.btn_delete_all)

        layout = QVBoxLayout(self)
        layout.addWidget(self.path_label)
        layout.addLayout(actions)
        layout.addWidget(self.media_list, stretch=1)
        layout.addWidget(self.preview_label)
        layout.addWidget(self.preview_info)

        self.set_directory(directory)

    def set_directory(self, directory):
        self.directory = directory
        self.load_media()

    def _iter_media_files(self):
        if not self.directory:
            return []
        base_path = Path(self.directory)
        if not base_path.exists() or not base_path.is_dir():
            return []
        return sorted(
            [p for p in base_path.iterdir() if p.is_file() and p.suffix.lower() in (IMAGE_EXTENSIONS | VIDEO_EXTENSIONS)],
            key=lambda p: p.name.lower(),
        )

    def load_media(self):
        self.path_label.setText(f"Directorio actual: {self.directory or 'No definido'}")
        self.media_list.clear()
        self.preview_label.setText("Selecciona un archivo para previsualizar")
        self.preview_label.setPixmap(QPixmap())
        self.preview_info.setText("")

        if not self.directory:
            self.media_list.addItem("Configura una ruta para visualizar archivos de media.")
            return

        base_path = Path(self.directory)
        if not base_path.exists() or not base_path.is_dir():
            self.media_list.addItem("La ruta no existe o no es un directorio válido.")
            return

        files = self._iter_media_files()
        for media_file in files:
            kind = "🎬" if media_file.suffix.lower() in VIDEO_EXTENSIONS else "🖼️"
            item = QListWidgetItem(f"{kind} {media_file.name}")
            item.setData(Qt.ItemDataRole.UserRole, str(media_file.resolve()))
            if self.selection_mode:
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Unchecked)
            self.media_list.addItem(item)

        if not files:
            self.media_list.addItem("No se encontraron fotos ni videos en la carpeta.")

    def open_item(self, item):
        media_path = item.data(Qt.ItemDataRole.UserRole)
        if not media_path:
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(media_path))

    def update_preview(self, current, _previous):
        if current is None:
            return

        media_path = current.data(Qt.ItemDataRole.UserRole)
        if not media_path:
            self.preview_label.setText("Selecciona un archivo válido para previsualizar")
            self.preview_label.setPixmap(QPixmap())
            self.preview_info.setText("")
            return

        file_path = Path(media_path)
        suffix = file_path.suffix.lower()
        self.preview_info.setText(f"Archivo: {file_path.name}")

        if suffix in IMAGE_EXTENSIONS:
            pixmap = QPixmap(str(file_path))
            if pixmap.isNull():
                self.preview_label.setText("No se pudo cargar la imagen")
                self.preview_label.setPixmap(QPixmap())
                return
            self.preview_label.setPixmap(
                pixmap.scaled(
                    self.preview_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            return

        if suffix in VIDEO_EXTENSIONS:
            cap = cv2.VideoCapture(str(file_path))
            ok, frame = cap.read()
            cap.release()
            if not ok or frame is None:
                self.preview_label.setText("No se pudo obtener preview del video")
                self.preview_label.setPixmap(QPixmap())
                return

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image = QImage(rgb.data, rgb.shape[1], rgb.shape[0], rgb.strides[0], QImage.Format.Format_RGB888)
            self.preview_label.setPixmap(
                QPixmap.fromImage(image).scaled(
                    self.preview_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_preview(self.media_list.currentItem(), None)

    def delete_selected_item(self):
        current = self.media_list.currentItem()
        if current is None:
            QMessageBox.information(self, "Sin selección", "Selecciona un elemento para borrar.")
            return

        media_path = current.data(Qt.ItemDataRole.UserRole)
        if not media_path:
            return

        confirm = QMessageBox.question(
            self,
            "Confirmar borrado",
            "¿Seguro que quieres borrar este archivo?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        path = Path(media_path)
        try:
            path.unlink(missing_ok=False)
        except FileNotFoundError:
            QMessageBox.warning(self, "No encontrado", "El archivo ya no existe.")
        except OSError as exc:
            QMessageBox.critical(self, "Error", f"No se pudo borrar: {exc}")
            return

        self.load_media()

    def toggle_selection_mode(self, state):
        self.selection_mode = state == Qt.CheckState.Checked.value
        self.btn_delete_all.setVisible(self.selection_mode)
        self.load_media()

    def delete_checked_items(self):
        checked_paths = []
        for i in range(self.media_list.count()):
            item = self.media_list.item(i)
            media_path = item.data(Qt.ItemDataRole.UserRole)
            if not media_path:
                continue
            if item.checkState() == Qt.CheckState.Checked:
                checked_paths.append(Path(media_path))

        if not checked_paths:
            QMessageBox.information(self, "Sin selección", "Marca al menos un elemento para borrar.")
            return

        confirm = QMessageBox.question(
            self,
            "Confirmar borrado múltiple",
            f"¿Seguro que quieres borrar {len(checked_paths)} archivo(s)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        errors = []
        for path in checked_paths:
            try:
                path.unlink(missing_ok=False)
            except OSError as exc:
                errors.append(f"{path.name}: {exc}")

        self.load_media()
        if errors:
            QMessageBox.warning(self, "Borrado parcial", "\n".join(errors))



class AddCameraDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Agregar cámara")
        self.setModal(True)

        self.input_mac = QLineEdit()
        self.input_mac.setPlaceholderText("AA:BB:CC:DD:EE:FF")

        self.input_user = QLineEdit()
        self.input_user.setPlaceholderText("admin")

        self.input_password = QLineEdit()
        self.input_password.setEchoMode(QLineEdit.EchoMode.Password)

        form = QFormLayout()
        form.addRow("MAC:", self.input_mac)
        form.addRow("Usuario:", self.input_user)
        form.addRow("Password:", self.input_password)

        self.input_tag = QLineEdit()
        self.input_tag.setPlaceholderText("Entrada, Bodega, Patio...")
        form.addRow("Tag:", self.input_tag)

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btn_ok = QPushButton("Guardar")
        btn_ok.setObjectName("primaryButton")
        btn_ok.clicked.connect(self.accept)

        actions = QHBoxLayout()
        actions.addStretch()
        actions.addWidget(btn_cancel)
        actions.addWidget(btn_ok)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(actions)

    def get_values(self):
        return (
            self.input_mac.text().strip(),
            self.input_user.text().strip(),
            self.input_password.text(),
            self.input_tag.text().strip(),
        )


class CameraListPanel(QWidget):
    HEADERS = ["MAC", "IP", "Usuario RTSP", "Contraseña RTSP", "Tag"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._widgets = []

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar por tag, IP o MAC")
        self.search_input.textChanged.connect(self._apply_filters)

        self.table = QTableWidget(0, len(self.HEADERS))
        self.table.setHorizontalHeaderLabels(self.HEADERS)
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)

        layout = QVBoxLayout(self)
        layout.addWidget(self.search_input)
        layout.addWidget(self.table, stretch=1)

    def set_widgets(self, widgets):
        self._widgets = widgets
        self._reload()

    def _reload(self):
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)

        for row, widget in enumerate(self._widgets):
            feed = widget.feed
            self.table.insertRow(row)
            values = [
                feed.mac or "",
                feed.ip or "",
                feed.usuario_raw or "",
                feed.password_raw or "",
                feed.tag or "",
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                self.table.setItem(row, col, item)

        self.table.resizeColumnsToContents()
        self.table.setSortingEnabled(True)
        self._apply_filters()

    def refresh_dynamic_values(self):
        for row, widget in enumerate(self._widgets):
            if row >= self.table.rowCount():
                break
            ip_item = self.table.item(row, 1)
            if ip_item is not None:
                ip_item.setText(widget.feed.ip or "")

    def _apply_filters(self):
        query = self.search_input.text().strip().lower()

        for row in range(self.table.rowCount()):
            mac = (self.table.item(row, 0).text() if self.table.item(row, 0) else "").lower()
            ip = (self.table.item(row, 1).text() if self.table.item(row, 1) else "").lower()
            tag = (self.table.item(row, 4).text() if self.table.item(row, 4) else "").lower()
            visible = not query or query in mac or query in ip or query in tag
            self.table.setRowHidden(row, not visible)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CCTV Responsive")
        self.resize(1200, 760)
        self.setMinimumSize(960, 620)

        central = QWidget()
        self.setCentralWidget(central)

        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(10)

        header_layout = QHBoxLayout()
        self.title_label = QLabel("Panel de cámaras")
        self.title_label.setObjectName("headerTitle")

        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        root_layout.addLayout(header_layout)

        self.grid_host = QWidget()
        self.grid = QGridLayout(self.grid_host)
        self.grid.setSpacing(12)
        self.grid.setContentsMargins(2, 2, 2, 2)

        self.tabs = QTabWidget()
        root_layout.addWidget(self.tabs, stretch=1)

        self._build_cameras_tab()
        self._build_media_tab()
        self._build_camera_list_tab()
        self._build_settings_tab()

        self.settings = load_settings()
        self._load_settings_inputs(self.settings)
        self._update_media_path_labels()
        self.media_window = None

        self.widgets = load_cameras(self.settings)
        self.build_grid()
        self.statusBar().showMessage("Sistema listo")

        self.table_refresh_timer = self.startTimer(2000)

    def _build_cameras_tab(self):
        cameras_tab = QWidget()
        layout = QVBoxLayout(cameras_tab)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(10)

        controls = QHBoxLayout()
        self.counter_label = QLabel("0 cámaras")
        self.counter_label.setObjectName("headerCounter")

        self.btn_add = QPushButton("➕ Agregar cámara")
        self.btn_add.setObjectName("primaryButton")
        self.btn_add.clicked.connect(self.add_camera_dialog)

        controls.addWidget(self.counter_label)
        controls.addStretch()
        controls.addWidget(self.btn_add)

        self.empty_label = QLabel("No hay cámaras configuradas. Usa ‘Agregar cámara’ para comenzar.")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setObjectName("emptyState")

        layout.addLayout(controls)
        layout.addWidget(self.empty_label)
        layout.addWidget(self.grid_host, stretch=1)

        self.tabs.addTab(cameras_tab, "Camaras")

    def _build_settings_tab(self):
        settings_tab = QWidget()
        layout = QVBoxLayout(settings_tab)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        info = QLabel("Estas credenciales se usan para mover y hacer zoom con pytapo.")
        info.setWordWrap(True)

        self.input_tapo_user = QLineEdit()
        self.input_tapo_user.setPlaceholderText("usuario@email.com")

        self.input_tapo_password = QLineEdit()
        self.input_tapo_password.setEchoMode(QLineEdit.EchoMode.Password)

        form = QFormLayout()
        form.addRow("Usuario / email:", self.input_tapo_user)
        form.addRow("Password:", self.input_tapo_password)

        self.btn_save_settings = QPushButton("Guardar credenciales")
        self.btn_save_settings.setObjectName("primaryButton")
        self.btn_save_settings.clicked.connect(self.save_settings_from_tab)

        actions = QHBoxLayout()
        actions.addStretch()
        actions.addWidget(self.btn_save_settings)

        tapo_group = QGroupBox("Credenciales Tapo")
        tapo_group_layout = QVBoxLayout(tapo_group)
        tapo_group_layout.addWidget(info)
        tapo_group_layout.addLayout(form)
        tapo_group_layout.addLayout(actions)

        self.input_media_directory = QLineEdit()
        self.input_media_directory.setPlaceholderText("Selecciona una carpeta de fotos/videos")
        self.btn_select_media_directory = QPushButton("Seleccionar carpeta")
        self.btn_select_media_directory.clicked.connect(self.select_media_directory)

        media_form = QFormLayout()
        media_form.addRow("Ruta:", self.input_media_directory)

        media_actions = QHBoxLayout()
        media_actions.addWidget(self.btn_select_media_directory)
        media_actions.addStretch()

        self.btn_save_media_directory = QPushButton("Guardar ruta de media")
        self.btn_save_media_directory.setObjectName("primaryButton")
        self.btn_save_media_directory.clicked.connect(self.save_media_directory_from_tab)
        media_actions.addWidget(self.btn_save_media_directory)

        media_group = QGroupBox("Configuración de directorios")
        media_group_layout = QVBoxLayout(media_group)
        media_group_layout.addLayout(media_form)
        media_group_layout.addLayout(media_actions)

        layout.addWidget(tapo_group)
        layout.addWidget(media_group)
        layout.addStretch()

        self.tabs.addTab(settings_tab, "Configuración")

    def _load_settings_inputs(self, settings):
        self.input_tapo_user.setText(settings.get("tapo_user", ""))
        self.input_tapo_password.setText(settings.get("tapo_password", ""))
        self.input_media_directory.setText(settings.get("media_directory", ""))

    def _build_media_tab(self):
        media_tab = QWidget()
        layout = QVBoxLayout(media_tab)
        layout.setContentsMargins(8, 8, 8, 8)

        info = QLabel("Visualiza, previsualiza y borra fotos/videos del directorio configurado.")
        info.setWordWrap(True)

        self.media_panel = MediaPanel("")

        layout.addWidget(info)
        layout.addWidget(self.media_panel, stretch=1)

        self.tabs.addTab(media_tab, "Multimedia")

    def _build_camera_list_tab(self):
        list_tab = QWidget()
        layout = QVBoxLayout(list_tab)
        layout.setContentsMargins(8, 8, 8, 8)

        info = QLabel("Listado consolidado de cámaras configuradas.")
        info.setWordWrap(True)

        self.camera_list_panel = CameraListPanel()

        layout.addWidget(info)
        layout.addWidget(self.camera_list_panel, stretch=1)

        self.tabs.addTab(list_tab, "Listado de cámaras")

    def _refresh_header(self):
        n = len(self.widgets)
        self.counter_label.setText(f"{n} cámara" if n == 1 else f"{n} cámaras")

    def build_grid(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        n = len(self.widgets)
        self._refresh_header()
        self.camera_list_panel.set_widgets(self.widgets)

        if n == 0:
            self.empty_label.show()
            self.grid_host.hide()
            return

        self.empty_label.hide()
        self.grid_host.show()

        cols = math.ceil(math.sqrt(n))
        rows = math.ceil(n / cols)

        for i, widget in enumerate(self.widgets):
            row, col = divmod(i, cols)
            self.grid.addWidget(widget, row, col)

        for row in range(rows):
            self.grid.setRowStretch(row, 1)
        for col in range(cols):
            self.grid.setColumnStretch(col, 1)

    def add_camera_dialog(self):
        dialog = AddCameraDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        mac, usuario, password, tag = dialog.get_values()
        if not mac or not usuario or not password:
            QMessageBox.warning(self, "Datos incompletos", "Completa MAC, usuario y password.")
            return

        self.add_camera(mac, usuario, password, tag)

    def save_settings_from_tab(self):
        tapo_settings = {
            "tapo_user": self.input_tapo_user.text().strip(),
            "tapo_password": self.input_tapo_password.text().strip(),
        }
        self.settings = update_settings(tapo_settings)

        for widget in self.widgets:
            widget.feed.set_settings(self.settings)

        self.statusBar().showMessage("Configuración de Tapo guardada", 3000)

    def select_media_directory(self):
        selected = QFileDialog.getExistingDirectory(
            self,
            "Seleccionar carpeta de media",
            self.input_media_directory.text().strip() or str(Path.home()),
        )
        if selected:
            self.input_media_directory.setText(selected)

    def save_media_directory_from_tab(self):
        media_directory = self.input_media_directory.text().strip()
        self.settings = update_settings({"media_directory": media_directory})
        self._update_media_path_labels()
        if self.media_window is not None:
            self.media_window.set_directory(media_directory)
        self.statusBar().showMessage("Ruta de media guardada", 3000)

    def _update_media_path_labels(self):
        media_directory = self.settings.get("media_directory", "")
        self.media_panel.set_directory(media_directory)

    def open_media_window(self):
        media_directory = self.settings.get("media_directory", "")
        if self.media_window is None:
            self.media_window = MediaPanel(media_directory)
            self.media_window.setWindowTitle("Galería de media")
            self.media_window.resize(800, 520)
        else:
            self.media_window.set_directory(media_directory)
        self.media_window.show()
        self.media_window.raise_()
        self.media_window.activateWindow()

    def add_camera(self, mac, usuario, password, tag=""):
        feed = CameraFeed(mac, usuario, password, tag=tag, settings=self.settings)
        feed.start()
        widget = CameraWidget(feed)
        self.widgets.append(widget)
        self.build_grid()
        save_cameras(self.widgets)
        self.statusBar().showMessage(f"Cámara {mac} agregada", 3000)

    def timerEvent(self, event):
        if event.timerId() == self.table_refresh_timer:
            self.camera_list_panel.refresh_dynamic_values()
        else:
            super().timerEvent(event)

    def closeEvent(self, event):
        for widget in self.widgets:
            widget.feed.stop()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_STYLE)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
