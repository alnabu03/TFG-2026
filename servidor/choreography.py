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
            
        comando_base = trozos[0].upper() 
        
        # --- PROCESAMIENTO ESPECIAL PARA MOTORES (4 palabras) ---
        if comando_base == "MOTORES":
            if len(trozos) != 4:
                raise ValueError(f"Línea {indice}: formato incorrecto. Usa 'MOTORES VEL_IZQ VEL_DER DURACION_MS'.")
            
            try:
                vel_izq = int(trozos[1])
                vel_der = int(trozos[2])
                duracion_ms = int(trozos[3])
                
                if duracion_ms <= 0:
                    raise ValueError(f"Línea {indice}: la duración debe ser mayor que 0.")
                    
                # Empaquetamos el comando para que el ESP32 lo entienda (MOTORES vel_izq vel_der)
                comando_completo = f"MOTORES {vel_izq} {vel_der}"
                pasos.append(PasoBaile(comando=comando_completo, duracion_ms=duracion_ms))
                
            except ValueError as error:
                raise ValueError(f"Línea {indice}: los parámetros de MOTORES deben ser números enteros.") from error

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

            if duracion_ms <= 0:
                raise ValueError(f"Línea {indice}: la duración debe ser mayor que 0.")

            pasos.append(PasoBaile(comando=comando_base, duracion_ms=duracion_ms)) 

    return pasos


class ReproductorBaile:
    def __init__(self,root,enviar_comando: Callable[[str, str], bool],escribir_log: Callable[[str], None],):
        self.root = root
        self.enviar_comando = enviar_comando
        self.escribir_log = escribir_log
        self.scheduled_lead_ms = 350

    def ejecutar_sincronizado(self,robots: list[str],pasos: list[PasoBaile],delay_inicio_ms: int = 1000,):#Recibe la lista de robots, los pasos a ejecutar y el delay inicial.
        if not robots:
            raise ValueError("No hay robots seleccionados.")
        if not pasos:
            raise ValueError("No hay pasos para ejecutar.")
        if delay_inicio_ms < 0:
            raise ValueError("El delay de inicio no puede ser negativo.")

        self.escribir_log(
            f"Baile sincronizado programado para {', '.join(robots)} en {delay_inicio_ms} ms"
        )
        self.root.after( #Programa la ejecución del primer paso del baile después del delay inicial, pasando la lista de robots, los pasos y el indice inicial (0) para empezar desde el primer paso.
            delay_inicio_ms,
            lambda: self._ejecutar_paso(robots=robots, pasos=pasos, indice=0),
        )

    def _ejecutar_paso(self, robots: list[str], pasos: list[PasoBaile], indice: int): #Ejecuta cada paso del baile de manera secuencia, enviando el comando a cada robot y luego programando el siguiente paso despues de la duracion del paso actual
        if indice >= len(pasos): 
            self.escribir_log(f"Baile finalizado para {', '.join(robots)}")
            return

        paso = pasos[indice]
        ok_robots = []
        ko_robots = []
        exec_at_ms = int(time.time() * 1000) + self.scheduled_lead_ms
        comando_programado = f"EXEC_AT_MS {exec_at_ms} {paso.comando}"
        if paso.duracion_ms > 0 and paso.comando != "PARA":
            comando_programado = f"{comando_programado} DUR_MS {paso.duracion_ms}"

        for robot_id in robots:
            ok = self.enviar_comando(robot_id, comando_programado)
            if ok:
                ok_robots.append(robot_id)
            else:
                ko_robots.append(robot_id)

        if ok_robots:
            self.escribir_log(
                f"Paso {indice + 1}/{len(pasos)} -> {paso.comando} ({paso.duracion_ms} ms) a {', '.join(ok_robots)}"
            )
        if ko_robots:
            self.escribir_log(
                f"No se pudo enviar {paso.comando} a: {', '.join(ko_robots)}"
            )

        self.root.after(
            paso.duracion_ms,
            lambda: self._ejecutar_paso(robots=robots, pasos=pasos, indice=indice + 1),
        )
