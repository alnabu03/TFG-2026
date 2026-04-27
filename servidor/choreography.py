from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable

COMANDOS_VALIDOS = {"AVANZA", "RETROCEDE", "IZQUIERDA", "DERECHA", "PARA"}
COMANDOS_GIRO_GRADOS = {"DERECHA_GRADOS", "IZQUIERDA_GRADOS"}


@dataclass
class PasoBaile:
    comando: str
    duracion_ms: int
    valor: float | None = None


def parsear_baile(texto: str) -> list[PasoBaile]:  #EL texto: str indica que se espera un string como argumento y el -> list[PasoBaile] indica que la función devuelve una lista de objetos PasoBaile.
    contenido = texto.strip() #quitamos espacios al principio y al final del texto para evitar problemas de formato.
    if not contenido:
        raise ValueError("El baile personalizado está vacío.")

    pasos: list[PasoBaile] = [] #Aqui se almacenarán los pasos del baile a medida que se van parseando. Se inicializa como una lista vacía de objetos PasoBaile.
    lineas = contenido.splitlines() #separamos el texto por lineas, si el usuario escribe 4 lineas, tendremos 4 strings en la lista de lineas.

    for indice, linea in enumerate(lineas, start=1): #Recorremos cada línea del texto con su índice (comenzando en 1).
        trozos = linea.strip().split() #Quitamos bordes y dividimos por espacios, por ejemplo "AVANZA 1000" se convierte en ["AVANZA", "1000"].
        if len(trozos) != 2: #Si no hay exactamente 2 partes (comando y duración), lanzamos un error indicando el formato correcto.
            raise ValueError(
                f"Línea {indice}: usa formato 'COMANDO DURACION_MS' o 'DERECHA_GRADOS/IZQUIERDA_GRADOS GRADOS'."
            )

        comando = trozos[0].upper() #Convertimos el comando a mayúsculas para que sea insensible a mayúsculas/minúsculas, por ejemplo "avanza" se convierte en "AVANZA".
        if comando not in COMANDOS_VALIDOS and comando not in COMANDOS_GIRO_GRADOS:
            raise ValueError(f"Línea {indice}: comando '{comando}' no válido.")

        if comando in COMANDOS_GIRO_GRADOS:
            try:
                grados = float(trozos[1].replace(",", "."))
            except ValueError as error:
                raise ValueError(f"Línea {indice}: grados no numéricos.") from error

            if grados <= 0:
                raise ValueError(f"Línea {indice}: los grados deben ser mayores que 0.")

            pasos.append(PasoBaile(comando=comando, duracion_ms=0, valor=grados))
            continue

        try:
            duracion_ms = int(trozos[1]) #Intentamos convertir la duración a un entero, si no es posible (por ejemplo, si el usuario escribe "mil" en lugar de "1000"), se lanzará un ValueError que capturamos para dar un mensaje de error más claro.
        except ValueError as error:
            raise ValueError(f"Línea {indice}: duración no numérica.") from error

        if duracion_ms <= 0:
            raise ValueError(f"Línea {indice}: la duración debe ser mayor que 0.")

        pasos.append(PasoBaile(comando=comando, duracion_ms=duracion_ms)) #Si todo es correcto, creamos un objeto PasoBaile con el comando y la duración y lo añadimos a la lista de pasos.

    return pasos


class ReproductorBaile:
    def __init__(
        self,
        root,
        enviar_comando: Callable[[str, str], bool],
        escribir_log: Callable[[str], None],
        ejecutar_giro_grados: Callable[[list[str], str, float, Callable[[], None]], None] | None = None,
    ):
        self.root = root
        self.enviar_comando = enviar_comando
        self.escribir_log = escribir_log
        self.ejecutar_giro_grados = ejecutar_giro_grados
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
        if paso.comando in COMANDOS_GIRO_GRADOS:
            if self.ejecutar_giro_grados is None:
                self.escribir_log(
                    f"No se puede ejecutar paso por grados ({paso.comando}) sin soporte ARUCO."
                )
                self.root.after(
                    0,
                    lambda: self._ejecutar_paso(robots=robots, pasos=pasos, indice=indice + 1),
                )
                return

            direccion = "DERECHA" if paso.comando == "DERECHA_GRADOS" else "IZQUIERDA"
            grados = float(paso.valor or 0.0)
            self.escribir_log(
                f"Paso {indice + 1}/{len(pasos)} -> giro {direccion} {grados:.1f}° con ARUCO para {', '.join(robots)}"
            )
            self.ejecutar_giro_grados(
                robots,
                direccion,
                grados,
                lambda: self.root.after(
                    0,
                    lambda: self._ejecutar_paso(
                        robots=robots, pasos=pasos, indice=indice + 1
                    ),
                ),
            )
            return

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
