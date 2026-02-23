APP_STYLE = """
QMainWindow {
    background: #dddfe3;
}

QWidget {
    font-family: 'Segoe UI';
    color: #4b5563;
    font-size: 13px;
}

QLabel#topBadge {
    margin-top: 8px;
    margin-bottom: 18px;
    padding: 10px 26px;
    border-radius: 8px;
    background: #a997cd;
    color: white;
    font-size: 28px;
    font-weight: 700;
}

QLabel#headerCounter {
    font-size: 13px;
    color: #6b7280;
    background: #f3f4f6;
    border: 1px solid #d1d5db;
    border-radius: 8px;
    padding: 6px 10px;
}

QPushButton {
    background: #f8fafc;
    color: #4b5563;
    border: 1px solid #cfd4dc;
    border-radius: 8px;
    padding: 8px 12px;
    font-weight: 600;
}

QPushButton#primaryButton {
    background: #a997cd;
    color: white;
    border-color: #9e8bc3;
}

QPushButton:hover {
    background: #eef2f7;
}

QPushButton#primaryButton:hover {
    background: #9986bf;
}

QWidget#cameraCard {
    background: #f6f7f9;
    border: 1px solid #c7cdd6;
    border-radius: 4px;
}

QWidget#cardHeader {
    min-height: 150px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}

QWidget#cameraCard[accent="coral"] QWidget#cardHeader {
    background: #f2694c;
}

QWidget#cameraCard[accent="green"] QWidget#cardHeader {
    background: #7cc86c;
}

QWidget#cameraCard[accent="cyan"] QWidget#cardHeader {
    background: #4ec0cf;
}

QLabel#cardTitle {
    color: rgba(255, 255, 255, 0.96);
    font-size: 18px;
    font-weight: 700;
}

QLabel#cardSubtitle {
    color: rgba(255, 255, 255, 0.85);
    font-size: 12px;
    font-weight: 600;
}

QLabel#statusLabel {
    margin: 0 10px;
    padding: 6px 10px;
    background: #e6e8ec;
    color: #6b7280;
    border-radius: 2px;
    font-size: 12px;
    font-weight: 600;
}

QLabel#videoLabel {
    margin: 0 10px;
    background: #f6f7f9;
    border: none;
    color: #9ca3af;
}

QLabel#emptyState {
    background: #f8fafc;
    border: 1px dashed #cfd4dc;
    color: #6b7280;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 600;
    padding: 28px;
}

QPushButton#padButton,
QPushButton#zoomButton {
    border-radius: 6px;
}

QStatusBar {
    background: #e9edf2;
    border-top: 1px solid #cfd4dc;
}
"""
