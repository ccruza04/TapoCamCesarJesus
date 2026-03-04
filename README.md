# CCTV Responsive

Aplicación de escritorio en **Python + PyQt6** para administrar cámaras Tapo con una interfaz clara, responsiva y orientada a operación diaria.

> Objetivo del proyecto: centralizar visualización, captura multimedia y configuración de cámaras en una sola interfaz, manteniendo una experiencia simple para el usuario final.

---

## 1) ¿Qué hace esta aplicación?

La app permite:

- Agregar y gestionar cámaras por **MAC**, usuario y contraseña.
- Resolver IP en red local y abrir stream **RTSP** automáticamente.
- Ver cámaras en una cuadrícula adaptable al número de dispositivos.
- Abrir una vista ampliada con controles **PTZ** (si `pytapo` está disponible).
- Tomar fotos y grabar videos por cámara.
- Explorar y borrar archivos multimedia desde un panel dedicado.
- Guardar configuración y cámaras para recuperar estado al reiniciar.

---

## 2) Características principales

### Gestión de cámaras
- Alta de cámara (MAC, usuario, contraseña, etiqueta/tag).
- Edición de cámaras existentes.
- Eliminación con confirmación.
- Listado tabular con búsqueda por MAC, IP o tag.

### Visualización
- Grid dinámico de cámaras.
- Tarjetas por cámara con estado de conexión.
- Apertura de ventana ampliada por doble clic.

### Multimedia
- Captura de foto (`.jpg`).
- Grabación de video (`.mp4`).
- Panel de multimedia con:
  - listado de archivos,
  - previsualización de imagen/video,
  - borrado simple y borrado múltiple.

### Configuración
- Credenciales globales para comandos PTZ mediante `pytapo`.
- Configuración de carpeta para guardar/leer fotos y videos.

---

## 3) Requisitos

- Python 3.8 o superior.
- `PyQt6`
- `opencv-python`
- `pytapo` (opcional para PTZ, recomendado)

Instalación rápida:

```bash
pip install PyQt6 opencv-python pytapo
```

---

## 4) Ejecución

Desde la carpeta `Dynamic_grid`:

```bash
python main.py
```

---

## 5) Flujo de uso recomendado

1. Ir al tab de **Configuración** y definir:
   - credenciales Tapo,
   - directorio de multimedia.
2. Ir al tab **Cámaras** y pulsar **➕ Agregar cámara**.
3. Completar MAC, usuario, contraseña y tag.
4. Verificar estado en la cuadrícula o en **Listado de cámaras**.
5. Doble clic en una cámara para abrir vista ampliada y usar PTZ / captura / grabación.
6. Revisar capturas en el tab **Multimedia**.

---

## 6) Estructura del proyecto

```text
Dynamic_grid/
├── main.py         # Interfaz principal y tabs de operación
├── funciones.py    # Lógica de feed, widgets de cámara y persistencia
├── estilos.py      # Hoja de estilos Qt (QSS)
├── cameras.dat     # Persistencia de cámaras
└── settings.json   # Persistencia de configuración (se crea automáticamente)
```

---

## 7) Componentes clave del código

- **MainWindow** (`main.py`): orquesta tabs, grid, listado y configuración.
- **MediaPanel** (`main.py`): explorador de fotos/videos con preview y borrado.
- **CameraFeed** (`funciones.py`): hilo de captura RTSP, reconexión, foto y grabación.
- **CameraWidget** (`funciones.py`): tarjeta de cámara para el grid.
- **CameraWindow** (`funciones.py`): vista ampliada con controles PTZ.
- **Persistencia** (`funciones.py`): carga/guardado de `settings` y `cameras`.

---

## 8) Notas técnicas

- Si no está instalado `pytapo`, la aplicación sigue funcionando para visualización/captura, pero los controles PTZ se deshabilitan.
- La detección de IP por MAC se realiza con ping + ARP en la red base configurada en `funciones.py` (`RED_BASE`).
- Las credenciales RTSP se codifican para URL, manteniendo compatibilidad con datos existentes.

---

## 9) Posibles mejoras futuras

- Integración de autenticación por perfiles de usuario.
- Soporte para múltiples segmentos de red.
- Detección de cámaras con escaneo concurrente optimizado.
- Exportación de eventos y auditoría de acciones.

---

## 10) Estado

Proyecto funcional para operación local de CCTV con enfoque en simplicidad de uso y persistencia básica.
