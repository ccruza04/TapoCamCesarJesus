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


class SettingsDialog(QDialog):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuración de Tapo")
        self.setModal(True)

        self.input_tapo_user = QLineEdit(settings.get("tapo_user", ""))
        self.input_tapo_user.setPlaceholderText("usuario@email.com")

        self.input_tapo_password = QLineEdit(settings.get("tapo_password", ""))
        self.input_tapo_password.setEchoMode(QLineEdit.EchoMode.Password)

        info = QLabel("Estas credenciales se usan para mover y hacer zoom con pytapo.")
        info.setWordWrap(True)

        form = QFormLayout()
        form.addRow("Usuario / email:", self.input_tapo_user)
        form.addRow("Password:", self.input_tapo_password)

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
        layout.addWidget(info)
        layout.addLayout(form)
        layout.addLayout(actions)

    def get_settings(self):
        return {
            "tapo_user": self.input_tapo_user.text().strip(),
            "tapo_password": self.input_tapo_password.text().strip(),
        }


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CCTV Responsive")
        self.resize(1200, 760)
        self.setMinimumSize(960, 620)

        central = QWidget()
        self.setCentralWidget(central)

        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(16, 14, 16, 14)
        root_layout.setSpacing(12)

        toolbar_layout = QHBoxLayout()
        toolbar_layout.setContentsMargins(4, 0, 4, 0)

        self.counter_label = QLabel("0 cámaras")
        self.counter_label.setObjectName("headerCounter")

        self.btn_add = QPushButton("➕ Agregar cámara")
        self.btn_add.setObjectName("primaryButton")
        self.btn_add.clicked.connect(self.add_camera_dialog)

        self.btn_config = QPushButton("⚙️ Configuración")
        self.btn_config.clicked.connect(self.open_settings_dialog)

        toolbar_layout.addWidget(self.counter_label)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(self.btn_config)
        toolbar_layout.addWidget(self.btn_add)
        root_layout.addLayout(toolbar_layout)

        self.top_badge = QLabel("▦")
        self.top_badge.setObjectName("topBadge")
        self.top_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root_layout.addWidget(self.top_badge, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.grid_host = QWidget()
        self.grid = QGridLayout(self.grid_host)
        self.grid.setSpacing(16)
        self.grid.setContentsMargins(4, 4, 4, 4)

        self.empty_label = QLabel("No hay cámaras configuradas. Usa ‘Agregar cámara’ para comenzar.")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setObjectName("emptyState")

        root_layout.addWidget(self.empty_label)
        root_layout.addWidget(self.grid_host, stretch=1)

        self.settings = load_settings()
        self.widgets = load_cameras(self.settings)
        self.build_grid()
        self.statusBar().showMessage("Sistema listo")

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

    def open_settings_dialog(self):
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.settings = dialog.get_settings()
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
