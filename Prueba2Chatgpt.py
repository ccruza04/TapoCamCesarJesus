import cv2
import time
import threading
import subprocess
import re
from tkinter import Tk, Label, Button
from PIL import Image, ImageTk
from urllib.parse import quote


# ================= CONFIG =================
MAC_OBJETIVO = "CC:BA:BD:22:C0:4D"   # MAC de la Tapo C210
USUARIO = "cepy_2026"
PASSWORD = "Castelar2026"
RED_BASE = "192.168.60."            # Red correcta
# =========================================


frame_actual = None
cap = None


# -------- BUSCAR IP POR MAC (WINDOWS) --------
def buscar_ip_por_mac(mac):
    print("[*] Poblando tabla ARP (rápido)...")
    mac = mac.lower().replace(":", "-")

    for i in range(1, 255):
        ip = f"{RED_BASE}{i}"
        print(f"   → Ping {ip}", end="\r")
        subprocess.call(
            f"ping -n 1 -w 100 {ip}",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=True
        )

        salida = subprocess.check_output(
            "arp -a",
            shell=True
        ).decode("cp1252", errors="ignore")

        for linea in salida.splitlines():
            if mac in linea.lower():
                encontrada = re.findall(r"\d+\.\d+\.\d+\.\d+", linea)
                if encontrada:
                    print(f"\n[+] IP encontrada: {encontrada[0]}")
                    return encontrada[0]

    print("\n[-] No se encontró la IP en la red")
    return None


# -------- CAPTURA RTSP --------
def capturar_video(rtsp_url):
    global frame_actual, cap

    # Forzar RTSP por TCP
    cap = cv2.VideoCapture(
        rtsp_url + "?rtsp_transport=tcp",
        cv2.CAP_FFMPEG
    )

    if not cap.isOpened():
        print("[-] No se pudo abrir el stream RTSP")
        return

    while True:
        ret, frame = cap.read()
        if ret:
            frame_actual = frame
        else:
            time.sleep(0.1)


# -------- GUARDAR IMAGEN --------
def guardar_imagen(prefijo):
    if frame_actual is not None:
        nombre = f"{prefijo}_{int(time.time())}.jpg"
        cv2.imwrite(nombre, frame_actual)
        print(f"[+] Imagen guardada: {nombre}")


# -------- GUI --------
def iniciar_gui():
    ventana = Tk()
    ventana.title("Tapo C210 - Viewer")
    ventana.resizable(False, False)

    lbl_video = Label(ventana)
    lbl_video.pack()

    def actualizar_video():
        if frame_actual is not None:
            img = cv2.cvtColor(frame_actual, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(img)
            img = img.resize((640, 360))
            imgtk = ImageTk.PhotoImage(image=img)
            lbl_video.config(image=imgtk)
            lbl_video.image = imgtk
        ventana.after(30, actualizar_video)

    Button(
        ventana,
        text="📸 Captura 1",
        width=20,
        command=lambda: guardar_imagen("captura_1")
    ).pack(pady=5)

    Button(
        ventana,
        text="📸 Captura 2",
        width=20,
        command=lambda: guardar_imagen("captura_2")
    ).pack(pady=5)

    actualizar_video()
    ventana.mainloop()


# ============ MAIN ============
print("[*] Buscando cámara en la red...")
ip = buscar_ip_por_mac(MAC_OBJETIVO)

if not ip:
    print("[-] No se encontró la IP de la cámara")
    exit()

# 🔐 Codificar credenciales (MUY IMPORTANTE)
usuario_enc = quote(USUARIO, safe="")
password_enc = quote(PASSWORD, safe="")

rtsp_url = f"rtsp://{usuario_enc}:{password_enc}@{ip}:554/stream1"
print(f"[+] Conectando a {rtsp_url}")

threading.Thread(
    target=capturar_video,
    args=(rtsp_url,),
    daemon=True
).start()

iniciar_gui()
