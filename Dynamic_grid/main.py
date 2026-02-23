import math
import sys

from PyQt6.QtWidgets import (
    QApplication,
    QInputDialog,
    QLineEdit,
    QGridLayout,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from estilos import APP_STYLE
from funciones import CameraFeed, CameraWidget, load_cameras, load_settings, save_cameras, save_settings


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CCTV Responsive")
        self.resize(1100, 700)
        self.setMinimumSize(900, 600)
        self.setMaximumSize(1400, 900)

        central = QWidget()
        self.setCentralWidget(central)

        vbox = QVBoxLayout(central)
        self.grid = QGridLayout()
        self.grid.setSpacing(10)
        self.grid.setContentsMargins(10, 10, 10, 10)
        vbox.addLayout(self.grid)

        self.btn_add = QPushButton("➕ Agregar Cámara")
        self.btn_add.clicked.connect(self.add_camera_dialog)
        vbox.addWidget(self.btn_add)

        self.btn_config = QPushButton("⚙️ Configuración pytapo")
        self.btn_config.clicked.connect(self.open_settings_dialog)
        vbox.addWidget(self.btn_config)

        self.settings = load_settings()
        self.widgets = load_cameras(self.settings)
        self.build_grid()

    def build_grid(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        n = len(self.widgets)
        if n == 0:
            return

        cols = math.ceil(math.sqrt(n))
        rows = math.ceil(n / cols)
        for i, widget in enumerate(self.widgets):
            row, col = divmod(i, cols)
            if row < rows:
                self.grid.addWidget(widget, row, col)

    def add_camera_dialog(self):
        mac, ok1 = QInputDialog.getText(self, "Nueva Cámara", "MAC:")
        if not ok1 or not mac:
            return

        usuario, ok2 = QInputDialog.getText(self, "Nueva Cámara", "Usuario:")
        if not ok2 or not usuario:
            return

        password, ok3 = QInputDialog.getText(
            self,
            "Nueva Cámara",
            "Password:",
            QLineEdit.EchoMode.Password,
        )
        if not ok3 or not password:
            return

        self.add_camera(mac, usuario, password)

    def open_settings_dialog(self):
        tapo_user, ok1 = QInputDialog.getText(
            self,
            "Configuración pytapo",
            "Usuario / email de Tapo:",
            text=self.settings.get("tapo_user", ""),
        )
        if not ok1:
            return

        tapo_password, ok2 = QInputDialog.getText(
            self,
            "Configuración pytapo",
            "Password de Tapo:",
            QLineEdit.EchoMode.Password,
            self.settings.get("tapo_password", ""),
        )
        if not ok2:
            return

        self.settings = {"tapo_user": tapo_user.strip(), "tapo_password": tapo_password.strip()}
        save_settings(self.settings)

        for widget in self.widgets:
            widget.feed.set_settings(self.settings)

    def add_camera(self, mac, usuario, password):
        feed = CameraFeed(mac, usuario, password, settings=self.settings)
        widget = CameraWidget(feed)
        self.widgets.append(widget)
        self.build_grid()
        save_cameras(self.widgets)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_STYLE)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
