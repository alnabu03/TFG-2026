import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
from choreography import parsear_baile, ReproductorBaile
import google.generativeai as genai
import threading


#Configuracion de la IA
GEMINI_API_KEY = "AIzaSyBd2VNgbvVbvn7BQfYBuZT_45_X0EcGk-w"
genai.configure(api_key=GEMINI_API_KEY)
modelo_ia = genai.GenerativeModel('gemini-2.5-flash')


class VentanaEstudioBailes:
    def __init__(self, parent_root, robots_seleccionados, enviar_comando, escribir_log):
        self.parent_root = parent_root
        self.robots= robots_seleccionados
        self.enviar_comando = enviar_comando
        self.escribir_log = escribir_log

        #Cramos la ventana secundaria
        self.window = tk.Toplevel(parent_root)
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
        prompt_oculto = f"""
        Eres el traductor del sistema de control de un robot móvil. 
        Tu única función es traducir las intenciones del usuario a un formato estricto de comandos.
        Los ÚNICOS comandos válidos son: AVANZA, RETROCEDE, IZQUIERDA, DERECHA, PARA.
        Cada comando debe ir seguido de un espacio y el tiempo en milisegundos (1 segundo = 1000 ms).
        Si el usuario no especifica tiempo, asume valores lógicos (minimo necesitamos 1000ms para que el paso se ejecute correctamente).
        REGLA DE ORO: Responde ÚNICAMENTE con la lista de comandos. No saludes, no uses markdown, no pongas comillas. Solo texto plano.
        
        Petición del usuario: "{peticion}"
        """
        try:
            respuesta = modelo_ia.generate_text(prompt=prompt_oculto) if hasattr(modelo_ia, 'generate_text') else modelo_ia.generate_content(prompt_oculto)
            codigo_generado = respuesta.text.strip()

            # Limpieza extra por si la IA devuelve bloques de código markdown
            codigo_generado = codigo_generado.replace("```", "").replace("python", "").replace("text", "").strip()

            # Volcamos el resultado en la caja de texto (usando root.after para volver al hilo principal de Tkinter)
            self.parent_root.after(0, lambda: self._volcar_resultado_ia(robot, codigo_generado, entry_widget))
        except Exception as e:
            self.parent_root.after(0, lambda: messagebox.showerror("Error IA", f"No se pudo conectar con la IA: {e}"))
            self.parent_root.after(0, lambda: entry_widget.config(state="normal"))

    def _volcar_resultado_ia(self, robot, codigo, entry_widget):
        caja_texto = self.cajas_texto[robot]
        caja_texto.delete("1.0", tk.END)
        caja_texto.insert("1.0", codigo + "\n")
        entry_widget.config(state="normal")
        self.escribir_log(f"IA ha generado una coreografía para la pista {robot}")

    def ejecutar_todo(self):
        try:
            delay = int(self.entry_delay.get())
            if delay < 0: raise ValueError
        except ValueError:
            messagebox.showerror("Error", "El delay debe ser un número positivo mayor que 0.")
            return 
        
        bailes_validados = {}

        for robot, caja in self.cajas_texto.items():
            contenido  = caja.get("1.0", tk.END).strip()
            if contenido: #Solo parseamos si hay texto
                try:
                    pasos = parsear_baile(contenido)
                    bailes_validados[robot] = pasos
                except  ValueError as e:
                    messagebox.showerror("Error de sintaxis", f"Error en la pista de {robot}:\n{str(e)}")
                    return 
        if not bailes_validados:
            messagebox.showwarning("Aviso", "Todas las pistas están vacías.")
            return
        self.escribir_log(f"Lanzando coreografía multipista para {len(bailes_validados)} robots...")

        #Asignamos un reproductor a cada robot y los disparamos a la vez
        for robot, pasos in bailes_validados.items():
            reproductor = ReproductorBaile(root=self.parent_root,enviar_comando=self.enviar_comando,escribir_log=self.escribir_log)
            reproductor.ejecutar_sincronizado([robot],pasos, delay)
