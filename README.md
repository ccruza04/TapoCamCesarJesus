Claro, aquí tienes un ejemplo de README para tu proyecto:

---

# CCTV Responsive

Este proyecto es una interfaz gráfica para gestionar cámaras de CCTV Tapo, desarrollada en Python usando PyQt6. Permite agregar cámaras mediante MAC, configurar credenciales globales, visualizar los feeds en una cuadrícula adaptable, y abrir vistas grandes para cada cámara, además de tomar fotos y gestionar configuraciones.

---

## Características

- Agregar y gestionar cámaras mediante MAC, usuario y contraseña.
- Configurar credenciales globales de Tapo.
- Visualización en cuadrícula responsiva de múltiples cámaras.
- Vista ampliada de la cámara con opción a tomar fotos.
- Persistencia de configuraciones y cámaras agregadas.
- Interfaz amigable y adaptable.

---

## Requisitos

- Python 3.8+
- PyQt6
- pytapo (para control de cámaras Tapo)
- Otros módulos necesarios (como `math`, `sys`)

Para instalar las dependencias:

```bash
pip install PyQt6 pytapo
```

---

## Uso

1. Ejecuta el script principal: 

```bash
python main.py
```

2. La ventana principal mostrará un panel donde puedes agregar cámaras, configurar credenciales globales y gestionar tus cámaras.

3. Para agregar una cámara, haz clic en "➕ Agregar cámara" y completa los datos.

4. Para modificar la configuración de Tapo, pulsa en "⚙️ Configuración Tapo".

5. Las cámaras se muestran en una cuadrícula adaptable. Haz clic en una cámara para abrir una vista en grande.

6. Desde la vista en grande, puedes tomar fotos o grabar (funcionalidad de grabación aún por implementar).

---

## Estructura del código

- **MainWindow**: ventana principal con la interfaz de gestión.
- **CameraFeed**: clase para gestionar cada feed de cámara.
- **CameraWidget**: widget para cada cámara en la cuadrícula.
- **AddCameraDialog**: diálogo para agregar nuevas cámaras.
- **SettingsDialog**: diálogo para configurar credenciales globales.
- **funciones.py**: funciones auxiliares para cargar y guardar configuraciones y cámaras.
- **estilos.py**: estilos CSS para la interfaz.

---

## Personalización y Extensiones

- Puedes agregar funcionalidad de grabación de video.
- Mejorar la detección de cámaras desconectadas.
- Añadir soporte para diferentes modelos o marcas de cámaras.
- Guardar las fotos y videos en directorios específicos.

---

## Licencia

Este proyecto es de uso personal y educativo. Modifícalo y extiéndelo según tus necesidades.

---

¿Quieres que te prepare también un ejemplo de estructura de archivos o algún apartado adicional?
