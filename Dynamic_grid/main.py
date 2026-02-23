import math
import sys

from PyQt6.QtWidgets import (
    QApplication,
    QGridLayout,
    QInputDialog,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from estilos import APP_STYLE
from funciones import CameraFeed, CameraWidget, load_cameras, save_cameras


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CCTV Responsive")
        self.resize(1200, 760)
        self.setMinimumSize(960, 620)

        central = QWidget()
        self.setCentralWidget(central)

        vbox = QVBoxLayout(central)
        self.grid = QGridLayout()
        self.grid.setSpacing(12)
        self.grid.setContentsMargins(14, 14, 14, 14)
        vbox.addLayout(self.grid)

        self.btn_add = QPushButton("➕ Agregar Cámara")
        self.btn_add.clicked.connect(self.add_camera_dialog)
        vbox.addWidget(self.btn_add)

        self.widgets = load_cameras()
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

        for i, w in enumerate(self.widgets):
            r, c = divmod(i, cols)
            self.grid.addWidget(w, r, c)

        for r in range(rows):
            self.grid.setRowStretch(r, 1)
        for c in range(cols):
            self.grid.setColumnStretch(c, 1)

    def add_camera_dialog(self):
        mac, ok1 = QInputDialog.getText(self, "Nueva Cámara", "MAC:")
        if not ok1 or not mac.strip():
            return

        usuario, ok2 = QInputDialog.getText(self, "Nueva Cámara", "Usuario:")
        if not ok2 or not usuario.strip():
            return

        password, ok3 = QInputDialog.getText(self, "Nueva Cámara", "Password:")
        if not ok3 or not password:
            return

        self.add_camera(mac.strip(), usuario.strip(), password)

    def add_camera(self, mac, usuario, password):
        feed = CameraFeed(mac, usuario, password)
        feed.start()
        widget = CameraWidget(feed)
        self.widgets.append(widget)
        self.build_grid()
        save_cameras(self.widgets)

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
