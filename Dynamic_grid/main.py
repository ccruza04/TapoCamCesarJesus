import math
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from estilos import APP_STYLE
from funciones import CameraFeed, CameraWidget, load_cameras, load_settings, save_cameras, save_settings


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

        self.settings = load_settings()
        self._load_settings_inputs(self.settings)

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

        self.btn_save_settings = QPushButton("Guardar configuración")
        self.btn_save_settings.setObjectName("primaryButton")
        self.btn_save_settings.clicked.connect(self.save_settings_from_tab)

        actions = QHBoxLayout()
        actions.addStretch()
        actions.addWidget(self.btn_save_settings)

        layout.addWidget(info)
        layout.addLayout(form)
        layout.addLayout(actions)
        layout.addStretch()

        self.tabs.addTab(settings_tab, "Configuración")

    def _load_settings_inputs(self, settings):
        self.input_tapo_user.setText(settings.get("tapo_user", ""))
        self.input_tapo_password.setText(settings.get("tapo_password", ""))

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
        self.settings = {
            "tapo_user": self.input_tapo_user.text().strip(),
            "tapo_password": self.input_tapo_password.text().strip(),
        }
        save_settings(self.settings)

        for widget in self.widgets:
            widget.feed.set_settings(self.settings)

        self.statusBar().showMessage("Configuración de Tapo guardada", 3000)

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
