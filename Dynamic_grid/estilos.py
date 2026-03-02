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

QLabel#headerTitle {
    font-size: 22px;
    font-weight: 700;
    color: #0b1324;
}

QLabel#headerCounter {
    font-size: 13px;
    font-weight: 600;
    color: #334155;
    padding: 6px 8px;
    background: rgba(255, 255, 255, 0.6);
    border-radius: 8px;
}

QPushButton {
    background-color: rgba(255, 255, 255, 0.78);
    color: #0f172a;
    border: 1px solid rgba(255, 255, 255, 0.9);
    border-radius: 10px;
    padding: 8px 14px;
    font-weight: 600;
}

QPushButton#primaryButton {
    background-color: #2563eb;
    color: white;
    border: 1px solid #1d4ed8;
}

QPushButton#primaryButton:hover {
    background-color: #1d4ed8;
}

QPushButton:hover {
    background-color: rgba(255, 255, 255, 0.95);
}

QPushButton:pressed {
    background-color: rgba(191, 219, 254, 0.95);
}

QPushButton#padButton {
    font-size: 16px;
    font-weight: 700;
    border-radius: 10px;
    padding: 4px;
}

QPushButton#zoomButton {
    font-size: 12px;
    font-weight: 700;
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

QLabel#emptyState {
    background: rgba(255, 255, 255, 0.72);
    border: 1px dashed #93c5fd;
    border-radius: 14px;
    color: #334155;
    font-size: 14px;
    font-weight: 600;
    padding: 28px;
}

QStatusBar {
    background: rgba(255, 255, 255, 0.55);
}
QTabWidget::pane {
    border: 1px solid rgba(255, 255, 255, 0.85);
    border-radius: 12px;
    background: rgba(255, 255, 255, 0.48);
    top: -1px;
}

QTabBar::tab {
    background: rgba(255, 255, 255, 0.72);
    border: 1px solid rgba(255, 255, 255, 0.9);
    border-bottom: none;
    padding: 8px 14px;
    margin-right: 6px;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
    font-weight: 600;
}

QTabBar::tab:selected {
    background: rgba(219, 234, 254, 0.95);
}

"""
