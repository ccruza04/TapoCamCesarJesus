# Sistema de Monitoreo CCTV Tapo (PyQt6)

Aplicación de escritorio para **administrar, visualizar y operar cámaras Tapo** desde una interfaz moderna en Python.

El proyecto fue simplificado para que sea más fácil de mantener:
- nombres en español,
- módulos con responsabilidades claras,
- flujo de trabajo directo para alta/edición/borrado de cámaras,
- documentación funcional de extremo a extremo.

---

## 1) ¿Qué hace esta aplicación?

Permite:

- Ver cámaras en una **grilla dinámica**.
- Dar de alta cámaras por **MAC + credenciales RTSP**.
- Editar o borrar cámaras desde el listado.
- Guardar fotos y videos en una carpeta configurable.
- Abrir una vista ampliada por cámara (doble clic).
- Usar controles PTZ (si `pytapo` está instalado y el modelo lo soporta).
- Navegar la galería local de media con previsualización.

---

## 2) Arquitectura simplificada

### `Dynamic_grid/main.py`
Contiene la interfaz principal:
- `VentanaPrincipal`: tabs, grilla, ajustes y ciclo de vida.
- `PanelMedia`: exploración y eliminación de archivos de media.
- `DialogoCamara`: formulario de alta/edición.
- `PanelListadoCamaras`: tabla de estado con acciones.

### `Dynamic_grid/funciones.py`
Contiene la lógica de negocio:
- `HiloCamara`: conexión RTSP, frame en memoria, grabación y foto.
- `TarjetaCamara`: preview compacta para la grilla.
- `VentanaCamara`: vista ampliada + botones de acción + PTZ.
- Funciones de persistencia:
  - `load_settings` / `update_settings`
  - `load_cameras` / `save_cameras`

### `Dynamic_grid/estilos.py`
Un único bloque de estilos (`ESTILO_APP`) para mantener la apariencia visual.

---

## 3) Requisitos

- Python 3.8+
- PyQt6
- OpenCV (`opencv-python`)
- `pytapo` (opcional para PTZ)

Instalación sugerida:

```bash
pip install PyQt6 opencv-python pytapo
```

> Si no instalas `pytapo`, la app funciona igual, pero desactiva controles PTZ.

---

## 4) Ejecución

Desde la raíz del repositorio:

```bash
python Dynamic_grid/main.py
```

---

## 5) Persistencia de datos

La aplicación usa dos archivos en la raíz del proyecto:

- `settings.json`: usuario/clave Tapo global y ruta de media.
- `cameras.dat`: listado de cámaras en formato JSON.

Esto permite reiniciar la app sin perder configuración.

---

## 6) Flujo de uso recomendado

1. Abrir app.
2. Ir a **Ajustes** y definir carpeta de media.
3. Agregar cámaras desde **➕ Agregar cámara**.
4. Ver preview en pestaña **Cámaras**.
5. Doble clic en una tarjeta para vista ampliada.
6. Gestionar inventario en pestaña **Listado**.
7. Revisar fotos/videos en **Galería**.

---

## 7) Decisiones de simplificación aplicadas

- Se redujo complejidad en clases UI y se centralizó la persistencia.
- Se estandarizaron nombres de métodos, variables y textos en español.
- Se mantuvieron alias de compatibilidad (`MainWindow`, `CameraFeed`, etc.) para evitar romper importaciones previas.
- Se dejó el código preparado para crecer por módulos sin acoplamiento fuerte.

---

## 8) Posibles mejoras futuras

- Descubrimiento de IP por MAC multiplataforma (actualmente orientado a comandos Windows).
- Tests automatizados de persistencia y validaciones de formularios.
- Paginación/filtros avanzados en la galería.
- Modo oscuro configurable.

---

## 9) Solución de problemas rápida

- **No se ve video**: validar IP/credenciales RTSP y conectividad de red.
- **No funciona PTZ**: instalar `pytapo` o revisar compatibilidad del modelo.
- **No se guarda media**: verificar permisos de escritura en la carpeta configurada.

---

## 10) Licencia y uso

Uso interno/educativo (ajustar según política de tu organización).
