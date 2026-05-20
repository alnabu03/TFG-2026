from __future__ import annotations
import time
from dataclasses import dataclass
from typing import Callable

COMANDOS_VALIDOS = {"AVANZA", "RETROCEDE", "IZQUIERDA", "DERECHA", "PARA", "MOTORES"}

@dataclass
class PasoBaile:
    comando: str
    duracion_ms: int
    valor: float | None = None
    robot_id: str | None = None  # NUEVO: Etiqueta para saber a qué robot pertenece el paso

def parsear_baile(texto: str) -> list[PasoBaile]:  
    contenido = texto.strip() 
    if not contenido:
        raise ValueError("El baile personalizado está vacío.")

    pasos: list[PasoBaile] = [] 
    lineas = contenido.splitlines() 

    for indice, linea in enumerate(lineas, start=1): 
        trozos = linea.strip().split() 
        if not trozos:
            continue
            
        # --- NUEVO: Detectar si la línea es para un robot específico ---
        robot_destino = None
        if trozos[0].upper().startswith("EP"): 
            robot_destino = trozos[0].upper()
            trozos = trozos[1:] # Quitamos la etiqueta para leer el comando normal
            if not trozos:
                continue
                
        comando_base = trozos[0].upper() 
        
        # --- PROCESAMIENTO ESPECIAL PARA MOTORES (4 palabras) ---
        if comando_base == "MOTORES":
            if len(trozos) != 4:
                raise ValueError(f"Línea {indice}: formato incorrecto. Usa 'MOTORES VEL_IZQ VEL_DER DURACION_MS'.")
            try:
                vel_izq, vel_der, duracion_ms = int(trozos[1]), int(trozos[2]), int(trozos[3])
                if duracion_ms <= 0: raise ValueError(f"Línea {indice}: duración > 0.")
                comando_completo = f"MOTORES {vel_izq} {vel_der}"
                pasos.append(PasoBaile(comando=comando_completo, duracion_ms=duracion_ms, robot_id=robot_destino))
            except ValueError as error:
                raise ValueError(f"Línea {indice}: parámetros numéricos.") from error

        # --- PROCESAMIENTO NORMAL PARA EL RESTO (2 palabras) ---
        else:
            if len(trozos) != 2: 
                raise ValueError(f"Línea {indice}: usa formato 'COMANDO DURACION_MS'.")
            if comando_base not in COMANDOS_VALIDOS:
                raise ValueError(f"Línea {indice}: comando '{comando_base}' no válido.")
            try:
                duracion_ms = int(trozos[1]) 
            except ValueError as error:
                raise ValueError(f"Línea {indice}: duración no numérica.") from error
            if duracion_ms <= 0: raise ValueError(f"Línea {indice}: duración > 0.")

            pasos.append(PasoBaile(comando=comando_base, duracion_ms=duracion_ms, robot_id=robot_destino)) 

    return pasos

class ReproductorBaile:
    def __init__(self, root, enviar_comando: Callable[[str, str], bool], escribir_log: Callable[[str], None]):
        self.root = root
        self.enviar_comando = enviar_comando
        self.escribir_log = escribir_log
        self.scheduled_lead_ms = 350

    def ejecutar_sincronizado(self, robots: list[str], pasos: list[PasoBaile], delay_inicio_ms: int = 1000):
        if not robots: raise ValueError("No hay robots seleccionados.")
        if not pasos: raise ValueError("No hay pasos para ejecutar.")

        self.escribir_log(f"Baile MULTIPISTA programado para {', '.join(robots)} en {delay_inicio_ms} ms")
        
        # Separamos la coreografía en listas individuales por robot
        listas_por_robot = {r: [] for r in robots}
        for paso in pasos:
            if paso.robot_id: # Si tiene etiqueta (ej. "EP1 AVANZA")
                if paso.robot_id in listas_por_robot:
                    listas_por_robot[paso.robot_id].append(paso)
            else: # Si no tiene etiqueta (ej. "AVANZA"), lo hacen todos
                for r in robots:
                    listas_por_robot[r].append(paso)

        # Lanzamos una línea de ejecución independiente para cada robot
        for robot_id, pasos_robot in listas_por_robot.items():
            if pasos_robot:
                self.root.after(delay_inicio_ms, lambda r=robot_id, p=pasos_robot: self._ejecutar_pista_individual(r, p, 0))

    def _ejecutar_pista_individual(self, robot_id: str, pasos: list[PasoBaile], indice: int):
        if indice >= len(pasos):
            self.escribir_log(f"Pista finalizada para {robot_id}")
            return

        paso = pasos[indice]
        exec_at_ms = int(time.time() * 1000) + self.scheduled_lead_ms
        comando_programado = f"EXEC_AT_MS {exec_at_ms} {paso.comando}"
        
        if paso.duracion_ms > 0 and paso.comando != "PARA":
            comando_programado = f"{comando_programado} DUR_MS {paso.duracion_ms}"

        ok = self.enviar_comando(robot_id, comando_programado)
        
        if ok:
            self.escribir_log(f"[{robot_id}] Paso {indice+1}/{len(pasos)}: {paso.comando} ({paso.duracion_ms}ms)")
        else:
            self.escribir_log(f"[{robot_id}] Error al enviar: {paso.comando}")

        # Programamos el siguiente paso de ESTE robot
        self.root.after(paso.duracion_ms, lambda r=robot_id, p=pasos, i=indice + 1: self._ejecutar_pista_individual(r, p, i))