import math
import sys
from pathlib import Path

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QApplication,
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
    QVBoxLayout,
    QWidget,
)

from estilos import APP_STYLE
from funciones import CameraFeed, CameraWidget, load_cameras, load_settings, save_cameras, update_settings


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".wmv", ".webm", ".m4v"}


class MediaBrowserWindow(QWidget):
    def __init__(self, directory):
        super().__init__()
        self.directory = directory
        self.setWindowTitle("Galería de media")
        self.resize(800, 520)

        self.path_label = QLabel()
        self.path_label.setWordWrap(True)

        self.media_list = QListWidget()
        self.media_list.itemDoubleClicked.connect(self.open_item)

        self.btn_refresh = QPushButton("Refrescar")
        self.btn_refresh.clicked.connect(self.load_media)

        actions = QHBoxLayout()
        actions.addStretch()
        actions.addWidget(self.btn_refresh)

        layout = QVBoxLayout(self)
        layout.addWidget(self.path_label)
        layout.addWidget(self.media_list, stretch=1)
        layout.addLayout(actions)

        self.load_media()

    def set_directory(self, directory):
        self.directory = directory
        self.load_media()

    def load_media(self):
        self.path_label.setText(f"Directorio actual: {self.directory or 'No definido'}")
        self.media_list.clear()

        if not self.directory:
            self.media_list.addItem("Configura una ruta para visualizar archivos de media.")
            return

        base_path = Path(self.directory)
        if not base_path.exists() or not base_path.is_dir():
            self.media_list.addItem("La ruta no existe o no es un directorio válido.")
            return

        files = [
            p for p in base_path.iterdir() if p.is_file() and p.suffix.lower() in (IMAGE_EXTENSIONS | VIDEO_EXTENSIONS)
        ]
        for media_file in sorted(files, key=lambda p: p.name.lower()):
            kind = "🎬" if media_file.suffix.lower() in VIDEO_EXTENSIONS else "🖼️"
            item = QListWidgetItem(f"{kind} {media_file.name}")
            item.setData(Qt.ItemDataRole.UserRole, str(media_file.resolve()))
            self.media_list.addItem(item)

        if not files:
            self.media_list.addItem("No se encontraron fotos ni videos en la carpeta.")

    def open_item(self, item):
        media_path = item.data(Qt.ItemDataRole.UserRole)
        if not media_path:
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(media_path))


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
        )


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
        self._build_settings_tab()
        self._build_media_tab()

        self.settings = load_settings()
        self._load_settings_inputs(self.settings)
        self._update_media_path_labels()
        self.media_window = None

        self.widgets = load_cameras(self.settings)
        self.build_grid()
        self.statusBar().showMessage("Sistema listo")

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

        self.tabs.addTab(cameras_tab, "Cámaras")

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

        info = QLabel("Abre una ventana para ver todas las fotos y videos del directorio configurado.")
        info.setWordWrap(True)

        self.media_tab_path_label = QLabel("Directorio actual: -")
        self.btn_open_media_window = QPushButton("Abrir ventana de media")
        self.btn_open_media_window.setObjectName("primaryButton")
        self.btn_open_media_window.clicked.connect(self.open_media_window)

        layout.addWidget(info)
        layout.addWidget(self.media_tab_path_label)
        layout.addWidget(self.btn_open_media_window, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addStretch()

        self.tabs.addTab(media_tab, "Media")

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

        mac, usuario, password = dialog.get_values()
        if not mac or not usuario or not password:
            QMessageBox.warning(self, "Datos incompletos", "Completa MAC, usuario y password.")
            return

        self.add_camera(mac, usuario, password)

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
        shown_path = media_directory if media_directory else "No definida"
        self.media_tab_path_label.setText(f"Directorio actual: {shown_path}")

    def open_media_window(self):
        media_directory = self.settings.get("media_directory", "")
        if self.media_window is None:
            self.media_window = MediaBrowserWindow(media_directory)
        else:
            self.media_window.set_directory(media_directory)
        self.media_window.show()
        self.media_window.raise_()
        self.media_window.activateWindow()

    def add_camera(self, mac, usuario, password):
        feed = CameraFeed(mac, usuario, password, settings=self.settings)
        feed.start()
        widget = CameraWidget(feed)
        self.widgets.append(widget)
        self.build_grid()
        save_cameras(self.widgets)
        self.statusBar().showMessage(f"Cámara {mac} agregada", 3000)

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
