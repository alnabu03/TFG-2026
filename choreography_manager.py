import threading
import time


class ChoreographyManager:
    def __init__(self, tcp_server, log_callback=None):
        self.tcp = tcp_server
        self.steps = []
        self.running = False
        self.thread = None
        self.log_callback = log_callback

    def log(self, texto):
        if self.log_callback:
            self.log_callback(texto)
        else:
            print(texto)

    def add_step(self, tiempo, robot_id, accion, duracion):
        paso = {
            "tiempo": float(tiempo),
            "robot": robot_id,
            "accion": accion.upper(),
            "duracion": float(duracion)
        }
        self.steps.append(paso)
        self.steps.sort(key=lambda x: x["tiempo"])

    def remove_step(self, index):
        if 0 <= index < len(self.steps):
            del self.steps[index]

    def clear_steps(self):
        self.steps.clear()

    def get_steps(self):
        return self.steps.copy()

    def load_preset(self, nombre):
        self.clear_steps()

        if nombre == "Saludo":
            self.add_step(0.0, "EP1", "AVANZA", 1.0)
            self.add_step(1.2, "EP1", "PARA", 0.0)
            self.add_step(1.5, "EP1", "IZQUIERDA", 0.8)
            self.add_step(2.5, "EP1", "PARA", 0.0)

        elif nombre == "Giro 2 robots":
            self.add_step(0.0, "EP1", "IZQUIERDA", 1.0)
            self.add_step(0.0, "EP2", "DERECHA", 1.0)
            self.add_step(1.2, "EP1", "PARA", 0.0)
            self.add_step(1.2, "EP2", "PARA", 0.0)

        elif nombre == "Avance sincronizado":
            self.add_step(0.0, "EP1", "AVANZA", 1.5)
            self.add_step(0.0, "EP2", "AVANZA", 1.5)
            self.add_step(1.7, "EP1", "PARA", 0.0)
            self.add_step(1.7, "EP2", "PARA", 0.0)

    def start(self):
        if self.running:
            self.log("Ya hay una coreografía en ejecución.")
            return

        self.running = True
        self.thread = threading.Thread(target=self._run_choreography, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        self.log("Coreografía detenida.")

    def _run_choreography(self):
        if not self.steps:
            self.log("No hay pasos en la coreografía.")
            self.running = False
            return

        self.log("Iniciando coreografía...")
        start_time = time.time()

        for paso in self.steps:
            if not self.running:
                self.log("Ejecución cancelada.")
                return

            while self.running and (time.time() - start_time) < paso["tiempo"]:
                time.sleep(0.01)

            if not self.running:
                self.log("Ejecución cancelada.")
                return

            robot_id = paso["robot"]
            accion = paso["accion"]
            duracion = paso["duracion"]

            mensaje = f"{robot_id} {accion}"
            ok = self.tcp.enviar_a_robot(robot_id, mensaje)

            if ok:
                self.log(f"Paso ejecutado: {mensaje}")
            else:
                self.log(f"No se pudo ejecutar: {mensaje}")
                continue

            if duracion > 0 and accion != "PARA":
                threading.Thread(
                    target=self._programar_parada,
                    args=(robot_id, duracion),
                    daemon=True
                ).start()

        self.running = False
        self.log("Coreografía terminada.")

    def _programar_parada(self, robot_id, duracion):
        time.sleep(duracion)

        if not self.running:
            return

        mensaje = f"{robot_id} PARA"
        ok = self.tcp.enviar_a_robot(robot_id, mensaje)

        if ok:
            self.log(f"Parada automática: {mensaje}")