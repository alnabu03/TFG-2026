import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
from choreography import parsear_baile, ReproductorBaile
import google.generativeai as genai
import threading


#Configuracion de la IA
GEMINI_API_KEY = "AIzaSyDxa9jIbAPd97xgqOj-f0d1ULgIwdV0je4"
genai.configure(api_key=GEMINI_API_KEY)
modelo_ia = genai.GenerativeModel('gemini-2.5-pro')


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

            tk.Label(frame_ia, text="✨ Pídele un baile a la IA:", bg="#f0f4f8", font=("Arial", 9, "bold")).pack(side="left", padx=10)   
            
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
        btn_ejecutar = tk.Button(ctrl_frame, text="▶ Ejecutar Coreografía Maestra", bg="#10b981", fg="white", font=("Arial", 11, "bold"), command=self.ejecutar_todo)
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

        prompt_oculto = f"""
        Eres el sistema de navegación avanzado de un robot. Recibes una imagen cenital de 640x480.
        
        LA CUADRÍCULA (TU REGLA VISUAL):
        - Las líneas AMARILLAS gruesas con texto marcan las centenas (0, 100, 200...).
        - Las líneas AZULES CLARAS finas marcan las mitades (50, 150, 250...).
        - El origen (0,0) está arriba a la izquierda. X crece a la derecha, Y crece hacia abajo.
        - Ten en cuenta que el robot mide 50x50 pixeles, así que su centro estará a 25 píxeles de su borde, tenlo en cuenta para evitar colisiones
        RAZONAMIENTO ESPACIAL OBLIGATORIO (Chain of Thought):
        Antes de generar los comandos de movimiento, DEBES analizar la escena escribiendo estas 3 líneas para anclar tu atención geométrica:
        ANÁLISIS_ROBOT: [coordenadas X, Y donde ves al robot]
        ANÁLISIS_OBSTÁCULOS: [coordenadas X, Y donde ves objetos a esquivar]
        ESTRATEGIA: [explica brevemente por qué puntos vas a pasar para rodearlo con seguridad]
        
        RUTA (FORMATO ESTRICTO):
        - Tus coordenadas X e Y DEBEN terminar siempre en 0 o en 50 (ej. 150, 200, 350). Prohibido usar números como 143 o 211.
        - Teniendo en cuenta lo que mide el robot calcula tu el margen que debemos tener para evitar colisiones.
        - Cada punto de la ruta debe estar en una línea nueva que empiece EXACTAMENTE por: MOVE X Y 0
        
        Petición del usuario para el robot {robot}: "{peticion}"
        """
        try:
            # 1. Tomamos la foto limpia
            frame = self.app_padre.capturar_foto_actual()
            
            if frame is not None:
                # --- VISUAL PROMPTING DE ALTA RESOLUCIÓN ---
                # Dibujamos líneas verticales (Eje X) cada 50 píxeles
                for x in range(0, 640, 50):
                    es_centena = (x % 100 == 0)
                    color = (0, 255, 255) if es_centena else (255, 255, 0) # Amarillo para 100s, Cyan para 50s (en BGR)
                    grosor = 2 if es_centena else 1
                    cv2.line(frame, (x, 0), (x, 480), color, grosor)
                    if es_centena:
                        cv2.putText(frame, f"X:{x}", (x+5, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                
                # Dibujamos líneas horizontales (Eje Y) cada 50 píxeles
                for y in range(0, 480, 50):
                    es_centena = (y % 100 == 0)
                    color = (0, 255, 255) if es_centena else (255, 255, 0) # Amarillo para 100s, Cyan para 50s (en BGR)
                    grosor = 2 if es_centena else 1
                    cv2.line(frame, (0, y), (640, y), color, grosor)
                    if es_centena:
                        cv2.putText(frame, f"Y:{y}", (5, y+20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                # -----------------------------------------------------------------

                # 2. Convertimos a formato PIL para enviarlo a Gemini
                imagen_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                imagen_pil = Image.fromarray(imagen_rgb)
                
                # Guardamos la foto para depuración (¡Échale un vistazo en tu carpeta!)
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

