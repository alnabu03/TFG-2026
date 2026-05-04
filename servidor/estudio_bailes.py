import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
from choreography import parsear_baile, ReproductorBaile

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
        self.window.minsize(600, 400)

        tk.Label(self.window, text="Ingrese la coreografía (un paso por línea, formato: COMANDO DUR_MS):", font=("Arial", 10, "italic")).pack(pady=10)

        self.notebook = ttk.Notebook(self.window)
        self.notebook.pack(fill="both",expand = True, padx = 15, pady = 5)

        self.cajas_texto = {}

        for robot in self.robots:
            frame_pista = tk.Frame(self.notebook)
            self.notebook.add(frame_pista, text = f"Pista {robot}")

            texto = tk.Text(frame_pista, height=15, font=("Consolas", 11))
            texto.pack(fill="both", expand=True, padx=10, pady=10)

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
