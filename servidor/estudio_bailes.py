import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
from choreography import parsear_baile, ReproductorBaile
import google.generativeai as genai
import threading


#Configuracion de la IA
GEMINI_API_KEY = "AIzaSyDxa9jIbAPd97xgqOj-f0d1ULgIwdV0je4"
genai.configure(api_key=GEMINI_API_KEY)
modelo_ia = genai.GenerativeModel('gemini-3.1-flash-lite')


class VentanaEstudioBailes:
    def __init__(self, app_padre, robots_seleccionados, enviar_comando, escribir_log):
        self.app_padre = app_padre
        self.robots= robots_seleccionados
        self.enviar_comando = enviar_comando
        self.escribir_log = escribir_log

        #Cramos la ventana secundaria
        self.window = tk.Toplevel(app_padre.root)
        self.window.title("Personalización de coreografías")
        self.window.geometry("800x500")
        self.window.minsize(600, 450)

        tk.Label(self.window, text="Ingrese la coreografía (un paso por línea, formato: COMANDO DUR_MS):", font=("Arial", 10, "italic")).pack(pady=10)

        self.notebook = ttk.Notebook(self.window)
        self.notebook.pack(fill="both",expand = True, padx = 15, pady = 5)

        self.cajas_texto = {}

        for robot in self.robots:
            frame_pista = tk.Frame(self.notebook)
            self.notebook.add(frame_pista, text = f"Pista {robot}")

            #barra para la inteligencia artificial--
            frame_ia = tk.Frame(frame_pista, bg="#f0f4f8", bd=1, relief="solid")
            frame_ia.pack(fill="x", padx=10, pady=(10, 0), ipady=5)

            tk.Label(frame_ia, text="✨ Pídele coordenadas de movimiento a la IA:", bg="#f0f4f8", font=("Arial", 9, "bold")).pack(side="left", padx=10)   
            
            entry_ia = tk.Entry(frame_ia, font=("Arial", 10))
            entry_ia.pack(side="left", fill="x", expand=True, padx=5)
            entry_ia.insert(0, "ej: haz un cuadrado de 2 segundos por lado")

            btn_ia = tk.Button(frame_ia, text="Generar código", bg="#8b5cf6", fg="white", cursor="hand2",command=lambda r=robot, e=entry_ia: self.llamar_ia(r, e))
            btn_ia.pack(side="right", padx=10)

            texto = tk.Text(frame_pista, height=15, font=("Consolas", 11))
            texto.pack(fill="both", expand=True, padx=10, pady=10)
            #--

            texto.insert("1.0", f"Ejemplo:\nAVANZA 1000\nPARA 300\n")
            self.cajas_texto[robot] = texto

        ctrl_frame = tk.Frame(self.window)
        ctrl_frame.pack(fill = "x", padx=15, pady=15)

        tk.Label(ctrl_frame, text="Delay inicio NTP (ms):").pack(side="left")
        self.entry_delay = tk.Entry(ctrl_frame, width=8)
        self.entry_delay.pack(side="left", padx=5)
        self.entry_delay.insert(0, "1500") # Un segundo y medio para que dé tiempo a calcular todo

            # Botón Maestro
        btn_ejecutar = tk.Button(ctrl_frame, text="▶ Ejecutar", bg="#10b981", fg="white", font=("Arial", 11, "bold"), command=self.ejecutar_todo)
        btn_ejecutar.pack(side = "right")



    def llamar_ia(self,robot,entry_widget): 
        peticion = entry_widget.get()
        if not peticion or peticion.startswith("ej:"):
            messagebox.showinfo("Aviso", "Escribe lo que quieras que haga el robot")
            return
            # Cambiamos el texto del botón temporalmente
        entry_widget.config(state="disabled")
        self.window.update()

        # Lanzamos la petición a Gemini en un hilo separado para no congelar la ventana
        threading.Thread(target=self._procesar_ia_thread, args=(robot, peticion, entry_widget), daemon=True).start()

    def _procesar_ia_thread(self, robot, peticion, entry_widget):
        import cv2
        from PIL import Image
        from vision_Aruco import detectar_poses_robot 
        #  - Líneas AZULES CLARAS = Mitades exactas (50, 150, 250...).

        prompt_oculto = f"""
        Eres el sistema de navegación avanzado de un robot móvil que se mueve mediante un controlador PID. Recibes una imagen cenital de 640x480.
        
        LA CUADRÍCULA (TU REGLA VISUAL):
        - Líneas AMARILLAS con texto = Centenas (X:0, X:100, Y:200...).
        - Origen (0,0) arriba a la izquierda. X crece a la DERECHA, Y crece hacia ABAJO.
        
        IDENTIFICACIÓN Y VOLUMEN (¡LOS OBJETOS NO SON PUNTOS!):
        - ROBOT: Cuadrado negro con dibujo blanco. IMPORTANTE: Fíjate que tiene un texto azul escrito encima (ej: "ID: 1 X: 230 Y: 380"). Lee ese texto y usa EXACTAMENTE esos números de X e Y como tu punto de partida real.
        - OBSTÁCULOS: Si hay obstáculos debes tener en cuenta que tienen anchura y altura...
        
        RAZONAMIENTO ESPACIAL (Chain of Thought OBLIGATORIO):
        Antes de dar la ruta, escribe EXACTAMENTE estas líneas para forzar tu percepción de los volúmenes:
        ANÁLISIS_ROBOT: [Centro en X, Y]
        BOUNDING_BOX_OBJETO_1 (SI LO HAY): [X_min a X_max, Y_min a Y_max]
        BOUNDING_BOX_OBJETO_2 (SI LO HAY): [X_min a X_max, Y_min a Y_max] (Si no hay un segundo objeto, omite esta línea)
        ESTRATEGIA: [Explica tu ruta garantizando que tus puntos NUNCA pisen el área de los Bounding Boxes. Añade siempre 50px extra de margen de seguridad en X y en Y respecto a esos límites].
        
        RUTA (FORMATO ESTRICTO):
        - Usa coordenadas que te permitan seguir el trazado que estimes óptimo (puedes usar incrementos de 25 píxeles como 125, 175, 225 si se requiere).
        - IMPORTANTE: NO incluyas la posición actual del robot en la lista. El primer comando MOVE debe ser el siguiente destino, nunca la coordenada donde ya se encuentra.
        - Cada línea debe ser: MOVE X Y 0
        - Piensa que cuantas menos coordenadas usemos, más fluido será el movimiento, pero recuerda que debemos cumplir con lo que se pide.

        Petición del usuario para el robot {robot}: "{peticion}"
        """
        try:
            # 1. Tomamos la foto limpia
            frame = self.app_padre.capturar_foto_actual()
            
            if frame is not None:

                # Creamos el detector ArUco rápido para esta foto
                aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
                aruco_params = cv2.aruco.DetectorParameters()
                detector = cv2.aruco.ArucoDetector(aruco_dict, aruco_params)
                
                # Esto detectará el robot y le pintará el texto "ID: 1 X: 230 Y: 350..."
                poses, frame = detectar_poses_robot(frame, detector)
                # --- VISUAL PROMPTING: Cuadrícula semitransparente + Texto Sólido ---
                overlay = frame.copy()
                
                # 1. Dibujamos SOLO las líneas en la capa transparente
                for x in range(0, 640, 50):
                    #es_centena = (x % 100 == 0)
                    #color = (0, 255, 255) if es_centena else (255, 255, 0)
                    #grosor = 2 if es_centena else 1
                    #cv2.line(overlay, (x, 0), (x, 480), color, grosor)
                    cv2.line(overlay, (x, 0), (x, 480), (0, 255, 255), 2) # Línea amarilla
                
                for y in range(0, 480, 50):
                    #es_centena = (y % 100 == 0)
                    #color = (0, 255, 255) if es_centena else (255, 255, 0)
                    #grosor = 2 if es_centena else 1
                    #cv2.line(overlay, (0, y), (640, y), color, grosor)
                    cv2.line(overlay, (0, y), (640, y), (0, 255, 255), 2) # Línea amarilla

                # Fusionamos al 50% para que las líneas se vean bien pero no tapen los obstáculos
                cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)

                # 2. Dibujamos los NÚMEROS directamente sobre el frame final (100% opacos)
                # y les ponemos un "borde negro" para que destaquen sobre la madera
                for x in range(0, 640, 100):
                    if x > 0:
                        texto = f"X:{x}"
                        # Borde negro (grosor 3)
                        cv2.putText(frame, texto, (x+5, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 3)
                        # Texto principal amarillo (grosor 1)
                        cv2.putText(frame, texto, (x+5, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

                for y in range(0, 480, 100):
                    if y > 0:
                        texto = f"Y:{y}"
                        # Borde negro
                        cv2.putText(frame, texto, (5, y+20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 3)
                        # Texto principal amarillo
                        cv2.putText(frame, texto, (5, y+20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
                # -----------------------------------------------------------------

                # 2. Convertimos a formato PIL para enviarlo a Gemini
                imagen_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                imagen_pil = Image.fromarray(imagen_rgb)
                
                # Guardamos la foto para depuración
                imagen_pil.save("foto_enviada_a_IA.jpg") 
                
                contenido_a_enviar = [prompt_oculto, imagen_pil]
                self.app_padre.root.after(0, lambda: self.escribir_log(f"📸 Enviando foto con SUB-CUADRÍCULA a la IA para {robot}..."))
            else:
                contenido_a_enviar = prompt_oculto
                self.app_padre.root.after(0, lambda: self.escribir_log("⚠️ Fallo al usar la cámara. Enviando solo texto a la IA."))

            respuesta = modelo_ia.generate_content(contenido_a_enviar)
            codigo_generado = respuesta.text.strip()

            # Limpieza extra
            codigo_generado = codigo_generado.replace("```", "").replace("python", "").replace("text", "").strip()

            self.app_padre.root.after(0, lambda: self._volcar_resultado_ia(robot, codigo_generado, entry_widget))
        except Exception as e:
            self.app_padre.root.after(0, lambda: messagebox.showerror("Error IA", f"No se pudo conectar con la IA: {e}"))
            self.app_padre.root.after(0, lambda: entry_widget.config(state="normal"))
    def _volcar_resultado_ia(self, robot, codigo, entry_widget):
        caja_texto = self.cajas_texto[robot]
        caja_texto.delete("1.0", tk.END)
        caja_texto.insert("1.0", codigo + "\n")
        entry_widget.config(state="normal")
        self.escribir_log(f"IA ha generado una coreografía para la pista {robot}")

    def ejecutar_todo(self):
        rutas_completas = {}
        for robot, caja in self.cajas_texto.items():
            contenido  = caja.get("1.0", tk.END).strip()
            if contenido:
                ruta_robot = []
                #ahora leemos el texto generado por la ia linea a linea
                for linea in contenido.splitlines():
                    partes = linea.split()
                    if len(partes) >= 4 and partes[0] == "MOVE":
                        try:
                            pto = {"x": float(partes[1]), "y": float(partes[2]), "theta": float(partes[3])}
                            ruta_robot.append(pto)
                        except ValueError:
                            pass # Ignoramos si hay alguna letra colada por error
                if ruta_robot:
                    rutas_completas[robot] = ruta_robot
        if not rutas_completas:
            messagebox.showwarning("Aviso", "No hay rutas válidas. Usa el formato 'MOVE X Y THETA'.")
            return
        self.escribir_log(f"Lanzando Coreografía con Waypoints PID para {len(rutas_completas)} robots...")
        # Aquí enviamos la lista completa de puntos de vuelta a tu archivo server_gui.py
        self.app_padre.iniciar_baile_waypoints(rutas_completas)

