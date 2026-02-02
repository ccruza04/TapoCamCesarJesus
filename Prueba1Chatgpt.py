import cv2
import time
import threading
import numpy as np
from scapy.all import ARP, Ether, srp
from tkinter import Tk, Button
from PIL import Image, ImageTk

# ================= CONFIG =================
MAC_OBJETIVO = "CC:BA:BD:22:C0:4D"   # <-- MAC de la Tapo C210
USUARIO = "cepy01_2026"
PASSWORD = "Castelar2026%"
INTERFAZ_RED = "192.168.60.208/24"
# =========================================

ip_encontrada = None
frame_actual = None

# -------- BUSCAR IP POR MAC --------
def buscar_ip_por_mac(mac):
    print("[*] Buscando IP por MAC...")
    arp = ARP(pdst=INTERFAZ_RED)
    ether = Ether(dst="ff:ff:ff:ff:ff:ff")
    paquete = ether / arp

    resultado = srp(paquete, timeout=3, verbose=0)[0]

    for enviado, recibido in resultado:
        if recibido.hwsrc.lower() == mac.lower():
            print(f"[+] IP encontrada: {recibido.psrc}")
            return recibido.psrc

    return None

# -------- CAPTURA RTSP --------
def capturar_video(rtsp_url):
    global frame_actual
    cap = cv2.VideoCapture(rtsp_url)

    if not cap.isOpened():
        print("[-] Error al conectar al stream RTSP")
        return

    while True:
        ret, frame = cap.read()
        if ret:
            frame_actual = frame

# -------- GUARDAR IMAGEN --------
def guardar_imagen(nombre):
    if frame_actual is not None:
        cv2.imwrite(nombre, frame_actual)
        print(f"[+] Imagen guardada: {nombre}")

# -------- INTERFAZ --------
def iniciar_gui(rtsp_url):
    ventana = Tk()
    ventana.title("Tapo C210 Viewer")

    lbl = Button(ventana)
    lbl.pack()

    def actualizar_frame():
        if frame_actual is not None:
            img = cv2.cvtColor(frame_actual, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(img)
            img = img.resize((640, 360))
            imgtk = ImageTk.PhotoImage(image=img)
            lbl.config(image=imgtk)
            lbl.image = imgtk
        ventana.after(30, actualizar_frame)

    Button(
        ventana,
        text="📸 Captura 1",
        command=lambda: guardar_imagen(f"captura_1_{int(time.time())}.jpg"),
        width=20
    ).pack(pady=5)

    Button(
        ventana,
        text="📸 Captura 2",
        command=lambda: guardar_imagen(f"captura_2_{int(time.time())}.jpg"),
        width=20
    ).pack(pady=5)

    actualizar_frame()
    ventana.mainloop()

# ================ MAIN =================
ip_encontrada = buscar_ip_por_mac(MAC_OBJETIVO)

if not ip_encontrada:
    print("[-] No se encontró la IP")
    exit()

rtsp = f"rtsp://{USUARIO}:{PASSWORD}@{ip_encontrada}:554/stream1"

threading.Thread(target=capturar_video, args=(rtsp,), daemon=True).start()
iniciar_gui(rtsp)
