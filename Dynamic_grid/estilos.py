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
    margin-top: 4px;
    margin-bottom: 14px;
    padding: 8px 24px;
    border-radius: 12px;
    background: #a997cd;
    color: white;
    font-size: 24px;
    font-weight: 700;
}

QLabel#headerCounter {
    font-size: 13px;
    color: #6b7280;
    background: #f5f6f8;
    border: 1px solid #d4d8df;
    border-radius: 12px;
    padding: 8px 12px;
}

QPushButton {
    background: #f9fafb;
    color: #4b5563;
    border: 1px solid #cfd4dc;
    border-radius: 12px;
    padding: 9px 14px;
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
    border: 1px solid #c9ced7;
    border-radius: 18px;
}

QWidget#cardHeader {
    min-height: 140px;
    border-top-left-radius: 18px;
    border-top-right-radius: 18px;
}

QWidget#cameraCard[accent="0"] QWidget#cardHeader { background: #f26d5b; }
QWidget#cameraCard[accent="1"] QWidget#cardHeader { background: #f29f5b; }
QWidget#cameraCard[accent="2"] QWidget#cardHeader { background: #7acb6d; }
QWidget#cameraCard[accent="3"] QWidget#cardHeader { background: #56c8b4; }
QWidget#cameraCard[accent="4"] QWidget#cardHeader { background: #4eb8d9; }
QWidget#cameraCard[accent="5"] QWidget#cardHeader { background: #6696e8; }
QWidget#cameraCard[accent="6"] QWidget#cardHeader { background: #8a7be4; }
QWidget#cameraCard[accent="7"] QWidget#cardHeader { background: #d26cc1; }

QLabel#cardTitle {
    color: rgba(255, 255, 255, 0.97);
    font-size: 15px;
    font-weight: 700;
}

QLabel#cardSubtitle {
    color: rgba(255, 255, 255, 0.88);
    font-size: 12px;
    font-weight: 600;
}

QLabel#statusLabel {
    margin: 0 14px;
    padding: 8px 12px;
    background: #e8ebf0;
    color: #5f6978;
    border-radius: 8px;
    font-size: 12px;
    font-weight: 600;
}

QLabel#videoLabel {
    margin: 0 14px;
    background: #0f172a;
    border: 1px solid #d7dbe3;
    border-radius: 12px;
    color: #cbd5e1;
}

QLabel#emptyState {
    background: #f8fafc;
    border: 1px dashed #cfd4dc;
    color: #6b7280;
    border-radius: 12px;
    font-size: 14px;
    font-weight: 600;
    padding: 28px;
}

QPushButton#padButton,
QPushButton#zoomButton {
    border-radius: 8px;
}

QStatusBar {
    background: #e9edf2;
    border-top: 1px solid #cfd4dc;
}
"""
