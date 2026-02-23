APP_STYLE = """
QMainWindow {
    background: #e5e7eb;
}

QWidget {
    font-family: 'Segoe UI';
    color: #334155;
    font-size: 13px;
}

QLabel#headerTitle {
    font-size: 24px;
    font-weight: 700;
    color: #0f172a;
}

QLabel#headerSubtitle {
    font-size: 13px;
    color: #64748b;
    font-weight: 500;
}

QLabel#topBadge {
    margin-top: 2px;
    margin-bottom: 10px;
    padding: 7px 20px;
    border-radius: 12px;
    background: #9b8ac9;
    color: white;
    font-size: 22px;
    font-weight: 700;
}

QLabel#headerCounter {
    font-size: 13px;
    color: #475569;
    background: #f8fafc;
    border: 1px solid #d4dae3;
    border-radius: 12px;
    padding: 9px 13px;
    font-weight: 600;
}

QPushButton {
    background: #ffffff;
    color: #334155;
    border: 1px solid #cfd8e3;
    border-radius: 12px;
    padding: 9px 14px;
    font-weight: 600;
}

QPushButton#primaryButton {
    background: #8b74c7;
    color: white;
    border-color: #7d64bd;
}

QPushButton:hover {
    background: #f1f5f9;
}

QPushButton#primaryButton:hover {
    background: #7c65b8;
}

QWidget#cameraCard {
    background: #f8fafc;
    border: 1px solid #cbd5e1;
    border-radius: 20px;
}

QWidget#cardHeader {
    min-height: 96px;
    border-top-left-radius: 20px;
    border-top-right-radius: 20px;
}

QWidget#cameraCard[accent="0"] QWidget#cardHeader { background: #f26d5b; }
QWidget#cameraCard[accent="1"] QWidget#cardHeader { background: #f3a15c; }
QWidget#cameraCard[accent="2"] QWidget#cardHeader { background: #7ecf71; }
QWidget#cameraCard[accent="3"] QWidget#cardHeader { background: #57c9b5; }
QWidget#cameraCard[accent="4"] QWidget#cardHeader { background: #4ab8de; }
QWidget#cameraCard[accent="5"] QWidget#cardHeader { background: #6a95ea; }
QWidget#cameraCard[accent="6"] QWidget#cardHeader { background: #8d7be5; }
QWidget#cameraCard[accent="7"] QWidget#cardHeader { background: #d86fbf; }

QLabel#cardTitle {
    color: rgba(255, 255, 255, 0.98);
    font-size: 18px;
    font-weight: 700;
}

QLabel#cardSubtitle {
    color: rgba(255, 255, 255, 0.9);
    font-size: 12px;
    font-weight: 600;
}

QLabel#statusLabel {
    margin: 0 14px;
    padding: 8px 12px;
    background: #edf2f7;
    color: #475569;
    border-radius: 10px;
    font-size: 12px;
    font-weight: 600;
}

QLabel#videoLabel {
    margin: 0 14px;
    background: #0f172a;
    border: 1px solid #d5dce6;
    border-radius: 14px;
    color: #cbd5e1;
}

QLabel#cardHint {
    margin: 0 14px;
    color: #64748b;
    font-size: 11px;
    font-weight: 600;
}

QLabel#emptyState {
    background: #f8fafc;
    border: 1px dashed #cbd5e1;
    color: #64748b;
    border-radius: 14px;
    font-size: 14px;
    font-weight: 600;
    padding: 28px;
}

QPushButton#padButton,
QPushButton#zoomButton {
    border-radius: 8px;
}

QStatusBar {
    background: #edf1f6;
    border-top: 1px solid #cfd8e3;
}
"""
