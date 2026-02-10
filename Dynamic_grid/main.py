import sys, math
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QGridLayout, QPushButton, QInputDialog, QVBoxLayout
from funciones import CameraFeed, CameraWidget, save_cameras, load_cameras
from estilos import APP_STYLE

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

        # boton agregar camara
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
        cols = math.ceil(math.sqrt(n))
        rows = math.ceil(n / cols)
        for i, w in enumerate(self.widgets):
            r, c = divmod(i, cols)
            self.grid.addWidget(w, r, c)

    def add_camera_dialog(self):
        mac, ok1 = QInputDialog.getText(self, "Nueva Cámara", "MAC:")
        if not ok1 or not mac:
            return
        usuario, ok2 = QInputDialog.getText(self, "Nueva Cámara", "Usuario:")
        if not ok2 or not usuario:
            return
        password, ok3 = QInputDialog.getText(self, "Nueva Cámara", "Password:")
        if not ok3 or not password:
            return
        self.add_camera(mac, usuario, password)

    def add_camera(self, mac, usuario, password):
        feed = CameraFeed(mac, usuario, password)
        feed.start()
        widget = CameraWidget(feed)
        self.widgets.append(widget)
        self.build_grid()
        save_cameras(self.widgets)

# ---------------- MAIN ----------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_STYLE)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
