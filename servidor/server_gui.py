import tkinter as tk
from tkinter import messagebox
import threading
import time
import traceback
import cv2
from choreography import PasoBaile, ReproductorBaile, parsear_baile
from discover import DiscoveryServer
from tcp_server import TcpServer
from vision_Aruco import detectar_poses_robot
from estudio_bailes import VentanaEstudioBailes
import math
from tkinter import filedialog
import os
ARUCO_FRAME_WIDTH = 640
ARUCO_FRAME_HEIGHT = 480
ARUCO_SAFE_MARGIN_PX = 70
ALIGN_CTRL_VERSION = "v4.0-go-to-pose-fsm"

BAILES_PREDEFINIDOS = {
    "Cuadrado corto": [
        PasoBaile("AVANZA", 1200),
        PasoBaile("DERECHA", 700),
        PasoBaile("AVANZA", 1200),
        PasoBaile("DERECHA", 700),
        PasoBaile("AVANZA", 1200),
        PasoBaile("DERECHA", 700),
        PasoBaile("AVANZA", 1200),
        PasoBaile("DERECHA", 700),
        PasoBaile("PARA", 300),
    ],
    "Zigzag": [
        PasoBaile("AVANZA", 700),
        PasoBaile("IZQUIERDA", 500),
        PasoBaile("AVANZA", 700),
        PasoBaile("DERECHA", 500),
        PasoBaile("AVANZA", 700),
        PasoBaile("IZQUIERDA", 500),
        PasoBaile("AVANZA", 700),
        PasoBaile("PARA", 300),
    ],
}


class ServerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Servidor de robots")
        self.root.geometry("980x760")
        self.root.minsize(880, 620)

        # Backend
        self.discovery = DiscoveryServer()
        self.tcp = TcpServer()
        self.tcp.levantar_servidor("0.0.0.0", 5000)
        self.hilo_camara_aruco = None
        self.detener_camara_aruco_evento = threading.Event()
        self.lock_detecciones_aruco = threading.Lock()
        self.detecciones_aruco_por_marker = {}
        self.detecciones_aruco_ts = 0.0
        self.hilo_alineacion = None
        self.detener_alineacion_evento = threading.Event()
        # ====== INTERFAZ ======
        contenedor_principal = tk.Frame(root)
        contenedor_principal.pack(padx=10, pady=10, fill="both", expand=True)

        self.canvas_scroll = tk.Canvas(contenedor_principal, highlightthickness=0)
        self.canvas_scroll.pack(side="left", fill="both", expand=True)

        barra_scroll = tk.Scrollbar(contenedor_principal,orient="vertical",command=self.canvas_scroll.yview,)
        barra_scroll.pack(side="right", fill="y")
        self.canvas_scroll.configure(yscrollcommand=barra_scroll.set)

        contenedor = tk.Frame(self.canvas_scroll)
        self.canvas_window = self.canvas_scroll.create_window((0, 0), window=contenedor, anchor="nw")
        contenedor.bind("<Configure>", self._actualizar_scroll_region)
        self.canvas_scroll.bind("<Configure>", self._ajustar_ancho_contenido)
        self.canvas_scroll.bind_all("<MouseWheel>", self._scroll_mousewheel_windows)

        # Lista de robots
        tk.Label(contenedor, text="Robots conectados (selección múltiple para sincronizar):").pack(anchor="w")

        self.lista_robots = tk.Listbox(contenedor,height=8,selectmode=tk.MULTIPLE,exportselection=False,)
        self.lista_robots.pack(fill="x", pady=(0, 10))

        frame_seleccion = tk.Frame(contenedor)
        frame_seleccion.pack(fill="x", pady=(0, 10))
        tk.Button(frame_seleccion, text="Seleccionar todos", command=self.seleccionar_todos).pack(side="left")
        tk.Button(frame_seleccion, text="Limpiar selección", command=self.limpiar_seleccion).pack(side="left", padx=8)

        # Entrada de comando
        tk.Label(contenedor, text="Comando para el robot seleccionado:").pack(anchor="w")

        self.entry_comando = tk.Entry(contenedor)
        self.entry_comando.pack(fill="x", pady=(0, 10))

        # Botón enviar
        self.boton_enviar = tk.Button(contenedor,text="Enviar comando",command=self.enviar_comando_manual)
        self.boton_enviar.pack(pady=(0, 10))
        
        # ===== VISION ARUCO =====
        frame_vision = tk.LabelFrame(contenedor, text="Visión ARUCO")
        frame_vision.pack(fill="x", pady=(0, 10))

        tk.Label(frame_vision, text="Fuente cámara (0 o URL):").grid(row=0, column=0, sticky="w", padx=6, pady=4)
        self.entry_fuente_aruco = tk.Entry(frame_vision)
        self.entry_fuente_aruco.grid(row=0, column=1, sticky="ew", padx=6, pady=4)
        self.entry_fuente_aruco.insert(0, "0")

        tk.Label(frame_vision, text="Objetivos (RobotID:x:y:theta):").grid(row=1, column=0, sticky="w", padx=6, pady=4)
        self.entry_objetivos_aruco = tk.Entry(frame_vision)
        self.entry_objetivos_aruco.grid(row=1, column=1, sticky="ew", padx=6, pady=4)
        self.entry_objetivos_aruco.insert(0, "EP1:300:300:0 EP2:700:300:0")

        tk.Label(frame_vision, text="Mapa marcadores (MarkerID:RobotID):").grid(row=2, column=0, sticky="w", padx=6, pady=4)
        self.entry_mapa_aruco = tk.Entry(frame_vision)
        self.entry_mapa_aruco.grid(row=2, column=1, sticky="ew", padx=6, pady=4)

        self.boton_autocompletar_mapa = tk.Button(frame_vision,text="Autocompletar mapa desde selección",command=self.autocompletar_mapa_aruco_desde_seleccion,)
        self.boton_autocompletar_mapa.grid(row=3, column=0, columnspan=2, sticky="w", padx=6, pady=(0, 4))

        self.usar_pid_servidor = tk.BooleanVar(value=False) # Por defecto, PID en el robot
        tk.Checkbutton(frame_vision, text="💻 Usar PID del Servidor (Experimental)", variable=self.usar_pid_servidor, font=("Arial", 9, "bold"), fg="#1e40af").grid(row=5, column=0, columnspan=2, sticky="w", padx=6, pady=5)

        self.modo_fluido = tk.BooleanVar(value=False) # Por defecto desactivado
        tk.Checkbutton(frame_vision, text="Modo Fluido (Ignorar orientación final)", variable=self.modo_fluido, font=("Arial", 9, "bold"), fg="#059669").grid(row=6, column=0, columnspan=2, sticky="w", padx=6, pady=5)
        
        frame_vision_botones = tk.Frame(frame_vision)
        frame_vision_botones.grid(row=4, column=0, columnspan=2, sticky="w", padx=6, pady=4)

        tk.Button(frame_vision_botones,text="Iniciar cámara ARUCO",command=self.iniciar_camara_aruco,).pack(side="left")
        tk.Button(frame_vision_botones,text="Detener cámara ARUCO",command=self.detener_camara_aruco,).pack(side="left", padx=6)
        tk.Button(frame_vision_botones,text="Iniciar posición inicial",command=self.iniciar_alineacion_inicial,).pack(side="left", padx=6)
        tk.Button(frame_vision_botones,text="Detener posición inicial",command=self.detener_alineacion_inicial,).pack(side="left", padx=6)
        frame_vision.grid_columnconfigure(1, weight=1)
        # Log
        tk.Label(contenedor, text="Log:").pack(anchor="w")
        self.text_log = tk.Text(contenedor, height=10, state="disabled")
        self.text_log.pack(fill="both", expand=True)
        # Enter para enviar
        self.entry_comando.bind("<Return>", lambda event: self.enviar_comando_manual())
        # ===== BOTONES DE CONTROL =====
        frame_botones = tk.Frame(contenedor)
        frame_botones.pack(pady=10)
        # AVANZA
        tk.Button(frame_botones, text="AVANZA", width=15,command=lambda: self.enviar_comando("AVANZA")).grid(row=0, column=1)
        # IZQUIERDA
        tk.Button(frame_botones, text="IZQUIERDA", width=15,command=lambda: self.enviar_comando("IZQUIERDA")).grid(row=1, column=0)
        # DERECHA
        tk.Button(frame_botones, text="DERECHA", width=15,command=lambda: self.enviar_comando("DERECHA")).grid(row=1, column=2)
        # RETROCEDE
        tk.Button(frame_botones, text="RETROCEDE", width=15,command=lambda: self.enviar_comando("RETROCEDE")).grid(row=2, column=1)
        # PARA
        tk.Button(frame_botones, text="PARA", width=15,command=lambda: self.enviar_comando("PARA")).grid(row=3, column=1)
        # ===== BAILES =====
        tk.Label(contenedor,text=("Baile personalizado (COMANDO DURACION_MS ):"),).pack(anchor="w")
        self.text_baile = tk.Text(contenedor, height=6)
        self.text_baile.pack(fill="x", pady=(0, 6))
        self.text_baile.insert( tk.END,"AVANZA 1000\n""IZQUIERDA 600\n""AVANZA 1000\n""PARA 300\n")
        
        frame_constructor_baile = tk.LabelFrame(contenedor, text="Constructor rápido de baile")
        frame_constructor_baile.pack(fill="x", pady=(0, 6))
        tk.Label(frame_constructor_baile, text="Comando:").grid(row=0, column=0, sticky="w", padx=(6, 4), pady=6)
        
        self.comando_constructor_var = tk.StringVar(value="AVANZA")
        tk.OptionMenu( frame_constructor_baile,self.comando_constructor_var,"AVANZA","RETROCEDE","IZQUIERDA","DERECHA","PARA",).grid(row=0, column=1, sticky="w", padx=(0, 8), pady=6)
        
        tk.Label(frame_constructor_baile, text="Duración (ms):").grid(row=0, column=2, sticky="w", padx=(0, 4), pady=6)
        self.entry_duracion_constructor_ms = tk.Spinbox(frame_constructor_baile,from_=100,to=10000,increment=100,width=8,)
        self.entry_duracion_constructor_ms.grid(row=0, column=3, sticky="w", padx=(0, 8), pady=6)
        self.entry_duracion_constructor_ms.delete(0, tk.END)
        self.entry_duracion_constructor_ms.insert(0, "1000")
        
        tk.Button(frame_constructor_baile,text="Añadir paso",command=self.agregar_paso_desde_constructor,).grid(row=0, column=4, sticky="w", padx=(0, 6), pady=6)
        tk.Button(frame_constructor_baile,text="Eliminar último paso",command=self.eliminar_ultimo_paso_baile,).grid(row=0, column=5, sticky="w", padx=(0, 6), pady=6)
        tk.Button(frame_constructor_baile,text="Limpiar baile",command=self.limpiar_baile_editado,).grid(row=0, column=6, sticky="w", padx=(0, 6), pady=6)

        frame_bailes = tk.Frame(contenedor)
        frame_bailes.pack(fill="x", pady=(0, 10))

        #VENTANA PARA BAILES PERSONALIZADOS
        self.boton_estudio = tk.Button(frame_bailes,text="🎵 Abrir Estudio Multipista",bg="#3b82f6", fg="white", font=("Arial", 9, "bold"),command=self.abrir_estudio_multipista)
        self.boton_estudio.pack(side="left", padx=8)

        self.boton_baile_personalizado = tk.Button(frame_bailes,text="Ejecutar baile creado",command=self.ejecutar_baile_personalizado)
        self.boton_baile_personalizado.pack(side="left")

        # ---  BOTONES DE CARGA TXT ---
        tk.Button(frame_bailes, text="📂 txt EP1", command=lambda: self.cargar_baile_robot("EP1")).pack(side="left", padx=2)
        tk.Button(frame_bailes, text="📂 txt EP2", command=lambda: self.cargar_baile_robot("EP2")).pack(side="left", padx=2)
        self.boton_baile_personalizado = tk.Button(frame_bailes,text="Ejecutar baile creado",command=self.ejecutar_baile_personalizado)
        # -----------------------------------

        self.baile_predefinido_var = tk.StringVar(value=list(BAILES_PREDEFINIDOS.keys())[0])
        self.menu_bailes = tk.OptionMenu(frame_bailes, self.baile_predefinido_var, *BAILES_PREDEFINIDOS.keys())
        self.menu_bailes.pack(side="left", padx=8)

        self.boton_baile_predefinido = tk.Button(frame_bailes,text="Cargar y ejecutar baile",command=self.ejecutar_baile_predefinido)
        self.boton_baile_predefinido.pack(side="left")

        tk.Label(contenedor,text="Delay de inicio sincronizado (ms):").pack(anchor="w")
        self.entry_delay_inicio = tk.Entry(contenedor)
        self.entry_delay_inicio.pack(fill="x", pady=(0, 10))
        self.entry_delay_inicio.insert(0, "1000")

        self.reproductor_baile = ReproductorBaile(root=self.root,enviar_comando=self.enviar_comando_simple,escribir_log=self.escribir_log,)
        self.root.protocol("WM_DELETE_WINDOW", self.on_cerrar)

        # Bucle principal
        self.update_loop()

    def on_cerrar(self):
        self.detener_camara_aruco()
        self.detener_alineacion_inicial()
        self.root.destroy()

    def _camara_aruco_activa(self) -> bool:
        return bool(self.hilo_camara_aruco and self.hilo_camara_aruco.is_alive())

    def _construir_mapa_robots_seleccionados(self) -> list[str]:
        robots = self.get_robots_seleccionados()
        if not robots:
            raise ValueError("Selecciona al menos un robot para mapear IDs ARUCO.")
        return [f"{indice}:{robot_id}" for indice, robot_id in enumerate(robots)]

    def _parsear_mapa_aruco_manual(self, mapa_texto: str) -> list[str]:
        mapa_tokens = [token for token in mapa_texto.split() if token]
        if not mapa_tokens:
            raise ValueError("Introduce al menos un mapeo en formato MarkerID:RobotID (ejemplo: 0:EP1 1:EP2).")
        marker_ids = set()
        robot_ids = set()
        resultado = []

        for token in mapa_tokens:
            if ":" not in token:
                raise ValueError(f"Formato inválido en '{token}'. Usa MarkerID:RobotID (ejemplo: 0:EP1).")
            marker_txt, robot_id = token.split(":", maxsplit=1)
            marker_txt = marker_txt.strip()
            robot_id = robot_id.strip()
            if marker_txt == "" or robot_id == "":
                raise ValueError(f"Formato inválido en '{token}'. MarkerID y RobotID son obligatorios.")
            try:
                marker_id = int(marker_txt)
            except ValueError as error:
                raise ValueError(f"MarkerID inválido en '{token}'. Debe ser un número entero.") from error
            if marker_id < 0:
                raise ValueError(f"MarkerID inválido en '{token}'. Debe ser mayor o igual a 0.")
            if marker_id in marker_ids:
                raise ValueError(f"MarkerID repetido: {marker_id}.")
            if robot_id in robot_ids:
                raise ValueError(f"RobotID repetido: {robot_id}.")

            marker_ids.add(marker_id)
            robot_ids.add(robot_id)
            resultado.append(f"{marker_id}:{robot_id}")

        return resultado

    def autocompletar_mapa_aruco_desde_seleccion(self):
        try:
            mapa_tokens = self._construir_mapa_robots_seleccionados()
        except ValueError as error:
            messagebox.showwarning("ARUCO", str(error))
            return
        self.entry_mapa_aruco.delete(0, tk.END)
        self.entry_mapa_aruco.insert(0, " ".join(mapa_tokens))
        self.escribir_log(f"Mapa ARUCO autocompletado: {', '.join(mapa_tokens)}")

    def _escribir_log_desde_hilo(self, texto):
        self.root.after(0, lambda: self.escribir_log(texto))

    def iniciar_camara_aruco(self):
        if self._camara_aruco_activa():
            messagebox.showinfo("ARUCO", "La cámara ARUCO ya está en ejecución.")
            return
        if self.hilo_alineacion and self.hilo_alineacion.is_alive():
            messagebox.showwarning("ARUCO","No se puede iniciar la cámara ARUCO mientras la alineación inicial está activa.",)
            return

        fuente = self.entry_fuente_aruco.get().strip() or "0"
        self.detener_camara_aruco_evento.clear()
        self.hilo_camara_aruco = threading.Thread(target=self._bucle_camara_aruco,args=(fuente,),daemon=True,)
        self.hilo_camara_aruco.start()
        self.escribir_log(f"Cámara ARUCO iniciada con fuente '{fuente}'.")

    def detener_camara_aruco(self):
        if not self._camara_aruco_activa():
            return
        self.detener_camara_aruco_evento.set()
        self.hilo_camara_aruco.join(timeout=1.2)
        self.hilo_camara_aruco = None
        self.escribir_log("Cámara ARUCO detenida.")

    def _bucle_camara_aruco(self, fuente_texto: str):
        if fuente_texto.isdigit():
            fuente_texto = int(fuente_texto)
        cap = cv2.VideoCapture(fuente_texto)
        if not cap.isOpened():
            self._escribir_log_desde_hilo(f"No se pudo abrir la cámara ARUCO.")
            return

        detector = cv2.aruco.ArucoDetector(cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50),cv2.aruco.DetectorParameters())
        ventana = "Fase 1 - Detección ARUCO"
        
        # --- NUEVO: Inicializar CSV de sincronismo ---
        with open("sincronismo_aruco.csv", "w") as f:
            f.write("timestamp,marker_id,x,y,theta\n")

        try:
            while not self.detener_camara_aruco_evento.is_set():
                ok, frame = cap.read()
                if not ok:
                    time.sleep(0.01)
                    continue
                poses_detectadas, frame_dibujado = detectar_poses_robot(frame, detector)
                
                #  Grabar datos en tiempo real ---
                ts_actual = time.time()
                with open("sincronismo_aruco.csv", "a") as f:
                    for marker_id, pose in poses_detectadas.items():
                        f.write(f"{ts_actual:.3f},{marker_id},{pose['x']},{pose['y']},{pose['theta']:.1f}\n")
                
                with self.lock_detecciones_aruco:
                    self.detecciones_aruco_por_marker = {
                        marker_id: pose["theta"] for marker_id, pose in poses_detectadas.items()
                    }
                    self.detecciones_aruco_ts = ts_actual

                cv2.imshow(ventana, frame_dibujado)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
        finally:
            cap.release()
            cv2.destroyWindow(ventana)
            with self.lock_detecciones_aruco:
                self.detecciones_aruco_por_marker = {}
                self.detecciones_aruco_ts = 0.0

    def iniciar_alineacion_inicial(self):
        if self.hilo_alineacion and self.hilo_alineacion.is_alive():
            messagebox.showinfo("Alineación", "La alineación inicial ya está en ejecución.")
            return
        if self._camara_aruco_activa():
            messagebox.showwarning("Alineación","Detén primero 'Iniciar cámara ARUCO': ambos flujos no deben usar la misma cámara al mismo tiempo.",)
            return

        objetivos = self.entry_objetivos_aruco.get().strip() 
        if not objetivos:
            messagebox.showwarning("Alineación", "Introduce al menos un objetivo RobotID:x:y:theta")
            return

        mapa_manual_texto = self.entry_mapa_aruco.get().strip()
        if mapa_manual_texto:
            try:
                mapa_tokens = self._parsear_mapa_aruco_manual(mapa_manual_texto)
            except ValueError as error:
                messagebox.showwarning("Alineación", str(error))
                return
        else:
            try:
                mapa_tokens = self._construir_mapa_robots_seleccionados()
            except ValueError as error:
                messagebox.showwarning("Alineación", str(error))
                return
            self.entry_mapa_aruco.delete(0, tk.END)
            self.entry_mapa_aruco.insert(0, " ".join(mapa_tokens))

        fuente = self.entry_fuente_aruco.get().strip() or "0"
        self.detener_alineacion_evento.clear()
        self.hilo_alineacion = threading.Thread(target=self._bucle_alineacion_inicial,args=(fuente, mapa_tokens, objetivos.split()),daemon=True,) #Crea el hilo para la alineación inicial, pasándole la fuente de video, el mapa de robots y los objetivos parseados.
        self.hilo_alineacion.start()#Inicia el hilo de alineacion inicial.
        self.escribir_log(f"Alineación inicial iniciada con mapa {', '.join(mapa_tokens)}")
        self.escribir_log(f"Control de alineación activo: {ALIGN_CTRL_VERSION}")

    def detener_alineacion_inicial(self):
        if not self.hilo_alineacion or not self.hilo_alineacion.is_alive():
            return
        self.detener_alineacion_evento.set()
        self.escribir_log("Alineación inicial detenida.")

    def _parsear_objetivos(self, tokens):
        objetivos = {}
        for token in tokens:
            robot_id, x_txt, y_txt, theta_txt = token.split(":", maxsplit=3)
            objetivos[robot_id] = {
                "x": int(float(x_txt)),
                "y": int(float(y_txt)),
                "theta": float(theta_txt),
            }
        return objetivos

    def _bucle_alineacion_inicial(self, fuente, mapa_tokens, objetivo_tokens):
        try:
            mapa = {}
            for token in mapa_tokens: #convertimos el mapa de texto a diccionario
                marker_txt, robot_id = token.split(":", maxsplit=1)
                mapa[int(marker_txt)] = robot_id

            objetivos = self._parsear_objetivos(objetivo_tokens)
            if set(mapa.values()) != set(objetivos.keys()):
                self._escribir_log_desde_hilo("Alineación: mapa y objetivos no coinciden en robots.")
                return

            aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
            aruco_params = cv2.aruco.DetectorParameters()
            detector = cv2.aruco.ArucoDetector(aruco_dict, aruco_params)

            if fuente.isdigit():
                fuente = int(fuente)
            cap = cv2.VideoCapture(fuente)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, ARUCO_FRAME_WIDTH)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, ARUCO_FRAME_HEIGHT)

            if not cap.isOpened():
                self._escribir_log_desde_hilo("Alineación: no se pudo abrir la cámara.")
                return
        
            frames_invalidos = 0
            max_frames_invalidos = 20
            #Creamos el archivo de telemetría
            with open("telemetria_pid.csv", "a") as f:
                f.write("tiempo,robot,x_act,y_act,th_act,x_obj,y_obj,th_obj,modo_pid\n")

            while not self.detener_alineacion_evento.is_set():
                ok, frame = cap.read()
                if not ok:
                    frames_invalidos += 1
                    if frames_invalidos == 1:
                        self._escribir_log_desde_hilo("Alineación: frame no válido (reintentando). ""Suele pasar si otra app/proceso está usando la misma cámara.")
                    if frames_invalidos >= max_frames_invalidos:
                        self._escribir_log_desde_hilo("Alineación: no se pudo leer la cámara tras varios intentos. ""Revisa la fuente y que no esté en uso por otro proceso.")
                        break
                    time.sleep(0.05)
                    continue

                frames_invalidos = 0
                poses_detectadas, frame_dibujado = detectar_poses_robot(frame, detector)
                pose_por_robot = {}
                for marker_id, pose in poses_detectadas.items(): #como detecciones tiene 2 objetos de tipo DeteccionMarcador, uno por cada marcador detectado, pues para cada deteccion, es decir, d1 y d2, tenemos marker_id, centro_x, centro_y y theta_grados. Entonces, si el marker_id de esa deteccion está en el mapa (es decir, si es uno de los marcadores que estamos usando para la alineación), entonces guardamos en pose_por_robot la información de posición y orientación de ese robot (usando el robot_id del mapa) para luego decidir qué acción tomar.  
                    if marker_id in mapa:
                        robot_id = mapa[marker_id]
                        pose_por_robot[robot_id] = pose 
                for robot_id, objetivo in objetivos.items(): #para cada robot que estamos alineando, sacamos su posicion actual con su posicion objetivo y la enviamos al robot.
                    if robot_id in pose_por_robot:
                        #1. Extraemos los datos que ve la cámara.
                        x_act = pose_por_robot[robot_id]["x"]
                        y_act = pose_por_robot[robot_id]["y"]
                        th_act = pose_por_robot[robot_id]["theta"]
                        #2. Extraemos los datos del objetivo.
                        x_obj = objetivo["x"]
                        y_obj = objetivo["y"]
                        th_obj = objetivo["theta"]
                        #3. Empaquetamos el mensaje para el ESP 
                        comando_pid = self._obtener_comando_segun_modo(robot_id, x_act, y_act, th_act, x_obj, y_obj, th_obj)                        # Obtenemos quién está calculando el PID
                        modo_actual = "SERVIDOR" if self.usar_pid_servidor.get() else "ESP32"
                        
                        # Guardo los datos en el csv añadiendo la etiqueta al final
                        with open("telemetria_pid.csv", "a") as f:
                            f.write(f"{time.time()},{robot_id},{x_act:.1f},{y_act:.1f},{th_act:.1f},{x_obj:.1f},{y_obj:.1f},{th_obj:.1f},{modo_actual}\n")
                        #4. Enviamos por tcp
                        self.enviar_comando_simple(robot_id, comando_pid)

                cv2.imshow("Alineación inicial", frame_dibujado)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
            for robot_id in objetivos.keys():
                self.enviar_comando_simple(robot_id, "PARA")
            cap.release()
            cv2.destroyWindow("Alineación inicial")
        except Exception as error:
            self._escribir_log_desde_hilo(f"Alineación: error inesperado: {error}")
            self._escribir_log_desde_hilo(traceback.format_exc())

    def iniciar_baile_waypoints(self, rutas):
        if self._camara_aruco_activa():
            messagebox.showwarning("Aviso", "Detén primero 'Iniciar cámara ARUCO'.")
            return
        
        fuente = self.entry_fuente_aruco.get().strip() or "0"
        mapa_manual_texto = self.entry_mapa_aruco.get().strip()
        mapa_tokens = self._parsear_mapa_aruco_manual(mapa_manual_texto) if mapa_manual_texto else self._construir_mapa_robots_seleccionados()

        self.detener_alineacion_evento.clear()
        self.hilo_alineacion = threading.Thread(target=self._bucle_baile_waypoints, args=(fuente, mapa_tokens, rutas), daemon=True)
        self.hilo_alineacion.start()
        self.escribir_log("Modo Baile por Waypoints (Máquina de estados) INICIADO.")

    def _bucle_baile_waypoints(self, fuente, mapa_tokens, rutas): #ESTA FUNCION NO LA PODEMOS REFACTORIZAR USANDO EL MENSAJE QUE ENVIA EL ROBOT AL SERVIDOR CUANDO LLEGA A UN OBJETO?
        try:
            mapa = {int(t.split(":")[0]): t.split(":")[1] for t in mapa_tokens}

            detector = cv2.aruco.ArucoDetector(cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50), cv2.aruco.DetectorParameters())
            cap = cv2.VideoCapture(int(fuente) if fuente.isdigit() else fuente)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

            #Todos los robots empiezan en el punto 0 de su ruta
            indices_ruta = {robot_id: 0 for robot_id in rutas.keys()}
            while not self.detener_alineacion_evento.is_set():
                ok, frame = cap.read()
                if not ok: continue

                poses_detectadas, frame_dibujado = detectar_poses_robot(frame, detector)
                pose_por_robot = {mapa[m_id]: p for m_id, p in poses_detectadas.items() if m_id in mapa}

                for robot_id, ruta in rutas.items():
                    if robot_id in pose_por_robot:
                        indice_actual = indices_ruta[robot_id]

                        #Si ya se han completado todos los puntos, lo ignoramos:
                        if indice_actual >= len(ruta):
                            continue
                    
                        objetivo = ruta[indice_actual]
                        x_act, y_act, th_act = pose_por_robot[robot_id]["x"], pose_por_robot[robot_id]["y"], pose_por_robot[robot_id]["theta"]
                        x_obj, y_obj, th_obj = objetivo["x"], objetivo["y"], objetivo["theta"]
                        # Comprobar si hemos llegado al punto actual
                        distancia = math.sqrt((x_obj - x_act)**2 + (y_obj - y_act)**2)
                        if distancia < 20.0:
                            self._escribir_log_desde_hilo(f"✅ {robot_id} alcanzó el punto {indice_actual+1}/{len(ruta)}")
                            
                            # Solo frenamos los motores si es el último punto de la ruta, 
                            # o si el usuario quiere que el movimiento sea robótico y estricto (no fluido)
                            if (indice_actual == len(ruta) - 1) or not self.modo_fluido.get():
                                self.enviar_comando_simple(robot_id, "PARA")
                                
                            indices_ruta[robot_id] += 1 # ¡AVANZAMOS AL SIGUIENTE ESTADO!
                        else:
                            comando_pid = f"PID_DATA {x_act:.1f} {y_act:.1f} {th_act:.1f} {x_obj:.1f} {y_obj:.1f} {th_obj:.1f}"
                            self.enviar_comando_simple(robot_id, comando_pid)

                cv2.imshow("Coreografía Inteligente (Waypoints)", frame_dibujado)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

            for robot_id in rutas.keys():
                self.enviar_comando_simple(robot_id, "PARA")
            cap.release()
            cv2.destroyWindow("Coreografía Inteligente (Waypoints)")
    
        except Exception as e:
            print(f"Error en el balie {e}")
        

    def _calcular_pid_servidor(self, robot_id, x_act, y_act, th_act, x_obj, y_obj, th_obj):
        import math

        # --- MEMORIA DEL ESTADO (Equivalente al 'static bool enFase2' de C++) ---
        if not hasattr(self, 'fase2_robots'):
            self.fase2_robots = {} # Creamos el diccionario si no existe
        if robot_id not in self.fase2_robots:
            self.fase2_robots[robot_id] = False # Por defecto, Fase 1

        dx = x_obj - x_act
        dy = y_obj - y_act
        error_dist = math.sqrt(dx*dx + dy*dy)

        # Control de histéresis
        if error_dist < 20.0:
            self.fase2_robots[robot_id] = True
        elif error_dist > 30.0:
            self.fase2_robots[robot_id] = False

        if self.fase2_robots[robot_id]:
            # === FASE 2: ROTACIÓN FINAL PARA AJUSTAR ORIENTACIÓN ===
            angulo_final_rad = th_obj * (math.pi / 180.0)
            angulo_actual_rad = th_act * (math.pi / 180.0)
            error_th_final = angulo_final_rad - angulo_actual_rad
            
            # Buscamos el ángulo más corto
            error_th_final = math.atan2(math.sin(error_th_final), math.cos(error_th_final))
            
            if abs(error_th_final) < 0.15:
                # OBJETIVO ALCANZADO (Devolvemos velocidades 0 y un aviso de terminado)
                self.fase2_robots[robot_id] = False # Reseteamos para el próximo waypoint
                return 0, 0, True 
            else:
                # Si hemos llegado pero no alineados, giramos sobre nosotros mismos
                vel_giro_final = 25.0 * error_th_final
                
                # Limitamos la velocidad de giro para no perder precisión
                if vel_giro_final > 20: vel_giro_final = 20
                if vel_giro_final < -20: vel_giro_final = -20
                
                pwm_min_giro = 15
                if 0 < vel_giro_final < pwm_min_giro: vel_giro_final = pwm_min_giro
                if 0 > vel_giro_final > -pwm_min_giro: vel_giro_final = -pwm_min_giro
                
                # Mover velocidades (izquierdo invertido para rotar sobre sí mismo)
                return int(-vel_giro_final), int(vel_giro_final), False

        # === FASE 1: ACERCAMIENTO ===
        angulo_objetivo_rad = math.atan2(-dy, dx)
        angulo_actual_rad = th_act * math.pi / 180.0
        error_ang = angulo_objetivo_rad - angulo_actual_rad
        
        # Normalizar a [-pi, pi]
        error_ang = math.atan2(math.sin(error_ang), math.cos(error_ang))
        
        if not hasattr(self, 'ultimo_error_ang_robots'):
            self.ultimo_error_ang_robots = {}
            self.ultimo_tiempo_pid_robots = {}
        if robot_id not in self.ultimo_error_ang_robots:
            self.ultimo_error_ang_robots[robot_id] = error_ang
            self.ultimo_tiempo_pid_robots[robot_id] = time.time()

        ahora = time.time()
        dt = ahora - self.ultimo_tiempo_pid_robots[robot_id]
        derivada_ang = (error_ang - self.ultimo_error_ang_robots[robot_id]) / dt
        if dt <= 0.001: dt = 0.001 # Evitar división por cero

        self.ultimo_error_ang_robots[robot_id] = error_ang
        self.ultimo_tiempo_pid_robots[robot_id] = ahora
        # Ajustes del PID idénticos a tu ESP32
        kp_dist = 0.5
        kp_ang = 60.0
        kd_ang  = 15.0 # Nuestro nuevo amortiguador
        velocidad_avance = kp_dist * error_dist
        if velocidad_avance > 120: 
            velocidad_avance = 120 # Limitamos para no perder precisión
            
        velocidad_giro = (kp_ang * error_ang) + (kd_ang * derivada_ang)        
        if abs(error_ang) > (math.pi / 4.0):
            velocidad_avance = 0 # Si el error es mayor de 90 grados, solo giramos
            
        vel_izquierda = velocidad_avance - velocidad_giro
        vel_derecha = velocidad_avance + velocidad_giro
        
        # Limitamos velocidades al rango del maqueen (0 a 255)
        if vel_izquierda > 255: vel_izquierda = 255
        if vel_izquierda < -255: vel_izquierda = -255
        if vel_derecha > 255: vel_derecha = 255
        if vel_derecha < -255: vel_derecha = -255
        
        # Buscamos el mínimo valor con el que el robot es capaz de moverse
        pwm_minimo = 15
        if 0 < vel_izquierda < pwm_minimo: vel_izquierda = pwm_minimo
        if 0 > vel_izquierda > -pwm_minimo: vel_izquierda = -pwm_minimo
        if 0 < vel_derecha < pwm_minimo: vel_derecha = pwm_minimo
        if 0 > vel_derecha > -pwm_minimo: vel_derecha = -pwm_minimo
        
        return int(vel_izquierda), int(vel_derecha), False



    def escribir_log(self, texto):
        self.text_log.config(state="normal")
        self.text_log.insert(tk.END, texto + "\n")
        self.text_log.see(tk.END)
        self.text_log.config(state="disabled")

    def get_robot_seleccionado(self): #????????????????????????????????????????????????????????????????????????????????????????????????
        seleccion = self.lista_robots.curselection()
        if not seleccion:
            return None
        return self.lista_robots.get(seleccion[0])

    def get_robots_seleccionados(self):
        seleccion = self.lista_robots.curselection()
        if not seleccion:
            return []
        return [self.lista_robots.get(indice) for indice in seleccion]

    def seleccionar_todos(self):
        self.lista_robots.selection_set(0, tk.END)

    def limpiar_seleccion(self):
        self.lista_robots.selection_clear(0, tk.END)

    def enviar_comando_manual(self):
        robots = self.get_robots_seleccionados()
        comando = self.entry_comando.get().strip().upper()

        if not robots:
            messagebox.showwarning("Aviso", "Selecciona al menos un robot")
            return

        if comando == "":
            messagebox.showwarning("Aviso", "Escribe un comando")
            return
        enviados = []
        fallidos = []
        for robot_id in robots:
            ok = self.enviar_comando_simple(robot_id, comando)
            if ok:
                enviados.append(robot_id)
            else:
                fallidos.append(robot_id)

        if enviados:
            self.escribir_log(f"Enviado '{comando}' a: {', '.join(enviados)}")
            self.entry_comando.delete(0, tk.END)
        if fallidos:
            self.escribir_log(f"No se pudo enviar a: {', '.join(fallidos)}")

    def refrescar_lista_robots(self):
        robots_actuales = list(self.tcp.clients.keys())

        seleccion_actual = set(self.get_robots_seleccionados())

        self.lista_robots.delete(0, tk.END)
        for robot_id in robots_actuales:
            self.lista_robots.insert(tk.END, robot_id)

        for indice, robot_id in enumerate(robots_actuales):
            if robot_id in seleccion_actual:
                self.lista_robots.selection_set(indice)

    def update_loop(self):
        robots_perdidos = self.discovery.step()
        self.tcp.aceptar()
        mensajes = self.tcp.leer_mensajes()
        
        for robot_id, texto in mensajes:
            if "ALCANZADO" in texto:
                self.escribir_log(f"✅ ¡El robot {robot_id} ha llegado a su destino!")
            else:
                # Opcional: imprimir otros mensajes que no sean ALCANZADO
                print(f"Mensaje de {robot_id}: {texto}")

        for robot_id in robots_perdidos:
            self.tcp.eliminar_cliente(robot_id)
            self.escribir_log(f"Robot perdido: {robot_id}")

        self.refrescar_lista_robots()

        self.root.after(200, self.update_loop)

    def enviar_comando(self, comando):
        robots = self.get_robots_seleccionados()
        if not robots:
            messagebox.showwarning("Aviso", "Selecciona al menos un robot")
            return

        enviados, fallidos = self.enviar_comando_sincronizado(robots, comando)
        if enviados:
            self.escribir_log(f"Enviado sincronizado '{comando}' a: {', '.join(enviados)}")
        if fallidos:
            self.escribir_log(f"No se pudo enviar a: {', '.join(fallidos)}")

    def ejecutar_baile_personalizado(self):
        robots = self.get_robots_seleccionados()
        if not robots:
            messagebox.showwarning("Aviso", "Selecciona al menos un robot")
            return

        try:
            pasos = parsear_baile(self.text_baile.get("1.0", tk.END))
            delay_inicio = self.get_delay_inicio()
        except ValueError as error:
            messagebox.showerror("Baile inválido", str(error))
            return

        self.escribir_log(
            f"Iniciando baile creado para {', '.join(robots)} ({len(pasos)} pasos)")
        self.reproductor_baile.ejecutar_sincronizado(robots=robots, pasos=pasos, delay_inicio_ms=delay_inicio)

    def ejecutar_baile_predefinido(self):
        robots = self.get_robots_seleccionados()
        if not robots:
            messagebox.showwarning("Aviso", "Selecciona al menos un robot")
            return

        nombre_baile = self.baile_predefinido_var.get()
        pasos = BAILES_PREDEFINIDOS.get(nombre_baile)
        if not pasos:
            messagebox.showerror("Error", "No se encontró el baile predefinido seleccionado.")
            return

        delay_inicio = self.get_delay_inicio()
        self.escribir_log(f"Cargando baile '{nombre_baile}' para {', '.join(robots)}")
        self.reproductor_baile.ejecutar_sincronizado(robots=robots, pasos=pasos, delay_inicio_ms=delay_inicio)

    def get_delay_inicio(self):
        texto = self.entry_delay_inicio.get().strip()
        if texto == "":
            return 1000
        try:
            delay = int(texto)
        except ValueError as error:
            raise ValueError("El delay de inicio debe ser numérico.") from error
        if delay < 0:
            raise ValueError("El delay de inicio debe ser mayor o igual que 0.")
        return delay

    def enviar_comando_simple(self, robot_id, comando):
        mensaje = f"{robot_id} {comando}"
        return self.tcp.enviar_a_robot(robot_id, mensaje)

    def enviar_comando_sincronizado(self, robots, comando, duracion_ms=0, lead_ms=350):
        exec_at_ms = int(time.time() * 1000) + lead_ms
        comando_programado = f"EXEC_AT_MS {exec_at_ms} {comando}"
        if duracion_ms > 0 and comando != "PARA":
            comando_programado = f"{comando_programado} DUR_MS {duracion_ms}"

        enviados = []
        fallidos = []
        for robot_id in robots:
            ok = self.enviar_comando_simple(robot_id, comando_programado)
            if ok:
                enviados.append(robot_id)
            else:
                fallidos.append(robot_id)
        return enviados, fallidos

    def _agregar_linea_baile(self, linea: str):
        texto_actual = self.text_baile.get("1.0", tk.END).rstrip()
        nuevo_texto = f"{texto_actual}\n{linea}\n" if texto_actual else f"{linea}\n"
        self.text_baile.delete("1.0", tk.END)
        self.text_baile.insert("1.0", nuevo_texto)

    def _actualizar_scroll_region(self, _event=None):
        self.canvas_scroll.configure(scrollregion=self.canvas_scroll.bbox("all"))

    def _ajustar_ancho_contenido(self, event):
        self.canvas_scroll.itemconfigure(self.canvas_window, width=event.width)

    def _scroll_mousewheel_windows(self, event):
        if event.delta == 0:
            return
        self.canvas_scroll.yview_scroll(int(-event.delta / 120), "units")

    def _obtener_duracion_ms_constructor(self) -> int:
        texto_duracion = self.entry_duracion_constructor_ms.get().strip()
        try:
            duracion_ms = int(texto_duracion)
        except ValueError as error:
            raise ValueError("La duración debe ser un entero en milisegundos.") from error
        if duracion_ms <= 0:
            raise ValueError("La duración debe ser mayor que 0 ms.")
        return duracion_ms

    def agregar_paso_desde_constructor(self):
        comando = self.comando_constructor_var.get().strip()
        try:
            duracion_ms = self._obtener_duracion_ms_constructor()
        except ValueError as error:
            messagebox.showerror("Paso inválido", str(error))
            return
        self._agregar_linea_baile(f"{comando} {duracion_ms}")
        self.escribir_log(f"Añadido al baile: {comando} {duracion_ms}")

    def eliminar_ultimo_paso_baile(self):
        lineas = [linea.strip() for linea in self.text_baile.get("1.0", tk.END).splitlines() if linea.strip()]
        if not lineas:
            messagebox.showinfo("Baile", "No hay pasos para eliminar.")
            return
        linea_eliminada = lineas.pop()
        self.text_baile.delete("1.0", tk.END)
        if lineas:
            self.text_baile.insert("1.0", "\n".join(lineas) + "\n")
        self.escribir_log(f"Paso eliminado del baile: {linea_eliminada}")

    def limpiar_baile_editado(self):
        self.text_baile.delete("1.0", tk.END)
        self.escribir_log("Baile editado limpiado.")

    def abrir_estudio_multipista(self):
        robots_seleccionados = self.get_robots_seleccionados()
        if not robots_seleccionados:
            messagebox.showwarning("Aviso", "Selecciona al menos un robot de la lista para abrir su pista de baile.")
            return
            
        # Abrimos la ventana pasándole las funciones que necesita para comunicarse
        VentanaEstudioBailes(app_padre=self, robots_seleccionados=robots_seleccionados, enviar_comando=self.enviar_comando_simple,escribir_log=self.escribir_log)

    def _obtener_comando_segun_modo(self, robot_id, x_act, y_act, th_act, x_obj, y_obj, th_obj):

        if hasattr(self, 'modo_fluido') and self.modo_fluido.get():
            th_obj = th_act

        if self.usar_pid_servidor.get():
            # El servidor hace la matemática y nos dice si hemos llegado
            pwm_izq, pwm_der, alcanzado = self._calcular_pid_servidor(robot_id, x_act, y_act, th_act, x_obj, y_obj, th_obj)
            
            if alcanzado:
                return "PARA"
            else:
                return f"MOTORES {pwm_izq} {pwm_der}"
        else:
            # Modo Original: El ESP32 se encarga
            return f"PID_DATA {x_act:.1f} {y_act:.1f} {th_act:.1f} {x_obj:.1f} {y_obj:.1f} {th_obj:.1f}"
        
        
    def cargar_baile_robot(self, robot_id):
        from tkinter import filedialog
        archivo_ruta = filedialog.askopenfilename(
            title=f"Seleccionar coreografía para {robot_id}",
            filetypes=[("Archivos de texto", "*.txt")]
        )
        
        if not archivo_ruta:
            return 
            
        try:
            with open(archivo_ruta, 'r', encoding='utf-8') as f:
                lineas = f.readlines()
            
            # Extraemos el texto que ya haya en la caja para no borrar al otro robot
            texto_actual = self.text_baile.get("1.0", tk.END).rstrip()
            if texto_actual:
                texto_actual += "\n"
                
            # Añadimos las líneas del archivo, inyectando la etiqueta del robot al inicio
            for linea in lineas:
                linea_limpia = linea.strip()
                if linea_limpia and not linea_limpia.startswith("#"):
                    texto_actual += f"{robot_id} {linea_limpia}\n"
                    
            self.text_baile.delete("1.0", tk.END)
            self.text_baile.insert("1.0", texto_actual + "\n")
            
            self.escribir_log(f"Coreografía de {robot_id} cargada y mezclada.")
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo leer el archivo: {e}")

    def capturar_foto_actual(self):
        # Lee la fuente de la interfaz (0 por defecto)
        fuente = self.entry_fuente_aruco.get().strip() or "0"
        cap = cv2.VideoCapture(int(fuente) if fuente.isdigit() else fuente)
        
        # Forzamos la resolución de tu tapete
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        ok, frame = cap.read()
        cap.release() # Soltamos la cámara enseguida para no bloquearla
        
        if ok:
            return frame
        return None

if __name__ == "__main__":
    root = tk.Tk()
    app = ServerGUI(root)
    root.mainloop()
