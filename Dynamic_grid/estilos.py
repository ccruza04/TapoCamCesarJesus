APP_STYLE = """
QMainWindow {
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 1,
        stop: 0 #eef3fb,
        stop: 1 #dbeafe
    );
}

QWidget {
    font-family: 'Segoe UI';
    color: #0f172a;
    font-size: 13px;
}

QPushButton {
    background-color: rgba(255, 255, 255, 0.78);
    color: #0f172a;
    border: 1px solid rgba(255, 255, 255, 0.9);
    border-radius: 10px;
    padding: 8px 14px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: rgba(255, 255, 255, 0.95);
}

QPushButton:pressed {
    background-color: rgba(191, 219, 254, 0.95);
}

QWidget#cameraCard {
    background-color: rgba(255, 255, 255, 0.62);
    border: 1px solid rgba(255, 255, 255, 0.9);
    border-radius: 16px;
}

QLabel#videoLabel {
    background-color: #020617;
    border-radius: 12px;
    color: #cbd5e1;
}

QLabel#statusLabel {
    color: #0f172a;
    font-size: 12px;
    font-weight: 600;
    padding-left: 4px;
}
"""
