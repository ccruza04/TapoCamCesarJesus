"""Estilos globales de la aplicación (Qt Style Sheet)."""

ESTILO_APP = """
QMainWindow {
    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1, stop: 0 #eef3fb, stop: 1 #dbeafe);
}

QWidget {
    font-family: 'Segoe UI';
    color: #0f172a;
    font-size: 13px;
}

QLabel#headerTitle {
    font-size: 22px;
    font-weight: 700;
}

QLabel#headerCounter {
    font-size: 13px;
    font-weight: 600;
    padding: 6px 8px;
    background: rgba(255, 255, 255, 0.60);
    border-radius: 8px;
}

QPushButton {
    background-color: rgba(255, 255, 255, 0.78);
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
    font-size: 12px;
    font-weight: 600;
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

QTabWidget::pane {
    border: 1px solid rgba(255, 255, 255, 0.85);
    border-radius: 12px;
    background: rgba(255, 255, 255, 0.48);
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

QTableWidget {
    background: rgba(255, 255, 255, 0.72);
    border: 1px solid rgba(255, 255, 255, 0.9);
    border-radius: 10px;
}
"""

# Compatibilidad con nombre anterior
APP_STYLE = ESTILO_APP
