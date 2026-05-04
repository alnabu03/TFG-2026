import csv
import math
import statistics
import matplotlib.pyplot as plt

def analizar_telemetria(archivo_csv):
    # Diccionario para guardar los datos separados por cada robot
    datos_por_robot = {}
    
    try:
        # Leer los datos guardados por tu servidor
        with open(archivo_csv, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:

                if row['tiempo'] == 'tiempo':
                    continue

                robot = row['robot']
                t = float(row['tiempo'])
                dx = float(row['x_obj']) - float(row['x_act'])
                dy = float(row['y_obj']) - float(row['y_act'])
                
                # Matemáticas correctas para el error de distancia (Teorema de Pitágoras)
                error_d = math.sqrt(dx**2 + dy**2) 
                
                # Si es la primera vez que vemos a este robot, le creamos su espacio
                if robot not in datos_por_robot:
                    datos_por_robot[robot] = []
                    
                datos_por_robot[robot].append({'t': t, 'error': error_d, 'dx': dx, 'dy': dy})
    except FileNotFoundError:
        print(f"Error: Archivo {archivo_csv} no encontrado.")
        return
    
    # 2. Separar los datos en "Intentos" (buscando pausas > 1 segundo)
    for robot, registros in datos_por_robot.items():
        intentos = []
        intento_actual = []


        for i in range(len(registros)):
            intento_actual.append(registros[i])
            
            # Si es la última línea o hay un salto de tiempo de más de 1 segundo -> Cortamos aquí
            if i == len(registros) - 1 or (registros[i+1]['t'] - registros[i]['t']) > 2.0:
                if len(intento_actual) > 5: # Filtramos clics accidentales muy cortos
                    intentos.append(intento_actual)
                intento_actual = []
                
        if not intentos:
            continue


        # 3. Extraer métricas de la foto-finish (último instante de cada intento)
        errores_finales = []
        tiempos_asentamiento = []
        errores_cuadraticos = []
        intentos_descartados = 0

        for intento in intentos:
            inicio_t = intento[0]['t']
            fin_t = intento[-1]['t']
            error_final = intento[-1]['error']

            if error_final > 40.0:
                intentos_descartados += 1
                continue
            
            errores_finales.append(error_final)
            tiempos_asentamiento.append(fin_t - inicio_t)
            errores_cuadraticos.append(intento[-1]['dx']**2 + intento[-1]['dy']**2)
            print(f"Se han descartado {intentos_descartados} intentos por fallos de visión/señal.")

        # 4. Cálculos Matemáticos para el TFG
        n = len(intentos)
        media_error = statistics.mean(errores_finales)
        desviacion = statistics.stdev(errores_finales) if n > 1 else 0.0
        rmse = math.sqrt(sum(errores_cuadraticos) / n)
        media_tiempo = statistics.mean(tiempos_asentamiento)

        # Imprimir en consola para copiar al documento
        print(f"\n" + "="*40)
        print(f"RESULTADOS ACADÉMICOS PARA: {robot}")
        print(f"Número de iteraciones (n): {n}")
        print(f"Error Medio Estacionario:  {media_error:.2f} px")
        print(f"Desviación Típica (σ):     ±{desviacion:.2f} px")
        print(f"Raíz del Error Cuadrático Medio (RMSE): {rmse:.2f} px")
        print(f"Tiempo Medio de Maniobra:  {media_tiempo:.2f} s")
        print("="*40 + "\n")

        # 5. Dibujar el Histograma
        plt.figure(figsize=(8, 5))
        # Creamos las barras agrupando los errores
        plt.hist(errores_finales, bins=8, color='#3b82f6', edgecolor='black', alpha=0.8)
        
        # Dibujamos una línea roja marcando dónde está la media
        plt.axvline(media_error, color='#ef4444', linestyle='dashed', linewidth=2, label=f'Media ({media_error:.2f} px)')
        
        plt.title(f'Distribución del Error de Posicionamiento - {robot} (n={n})', fontsize=13, fontweight='bold')
        plt.xlabel('Error final respecto al objetivo (píxeles)', fontsize=11)
        plt.ylabel('Frecuencia (Nº de maniobras)', fontsize=11)
        plt.grid(axis='y', linestyle='--', alpha=0.6)
        plt.legend()
        
        nombre_archivo = f'histograma_{robot}.png'
        plt.savefig(nombre_archivo, dpi=300, bbox_inches='tight')
        print(f"📊 Histograma de alta resolución guardado como '{nombre_archivo}'")
        plt.show()

if __name__ == "__main__":
    analizar_telemetria("telemetria_pid.csv")