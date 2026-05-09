import csv
import math
import statistics
import matplotlib.pyplot as plt

def analizar_telemetria(archivo_csv):
    # Diccionario para guardar los datos separados por cada robot Y MODO
    datos_por_robot = {}
    
    try:
        with open(archivo_csv, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['tiempo'] == 'tiempo':
                    continue

                robot = row['robot']
                t = float(row['tiempo'])
                dx = float(row['x_obj']) - float(row['x_act'])
                dy = float(row['y_obj']) - float(row['y_act'])
                
                # --- NUEVO: Leer la columna del modo (con valor por defecto por si hay datos viejos) ---
                modo_pid = row.get('modo_pid', 'ESP32').strip()
                
                # --- NUEVO: Creamos una clave combinada (Ej: "EP1_SERVIDOR") ---
                clave_grupo = f"{robot}_{modo_pid}"
                
                error_d = math.sqrt(dx**2 + dy**2) 
                
                if clave_grupo not in datos_por_robot:
                    datos_por_robot[clave_grupo] = []
                    
                datos_por_robot[clave_grupo].append({'t': t, 'error': error_d, 'dx': dx, 'dy': dy})
    except FileNotFoundError:
        print(f"Error: Archivo {archivo_csv} no encontrado.")
        return
    
    # 2. Separar los datos en "Intentos" 
    # --- NUEVO: Ahora iteramos sobre la clave combinada ---
    for clave_grupo, registros in datos_por_robot.items():
        intentos = []
        intento_actual = []

        for i in range(len(registros)):
            intento_actual.append(registros[i])
            
            if i == len(registros) - 1 or (registros[i+1]['t'] - registros[i]['t']) > 2.0:
                if len(intento_actual) > 5: 
                    intentos.append(intento_actual)
                intento_actual = []
                
        if not intentos:
            continue

        # 3. Extraer métricas de la foto-finish
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
            
        if intentos_descartados > 0:
            print(f"Se han descartado {intentos_descartados} intentos en {clave_grupo} por fallos de visión/señal.")

        # Evitar división por cero si se descartaron todos
        if not errores_finales:
            continue

        # 4. Cálculos Matemáticos para el TFG
        n = len(intentos) - intentos_descartados
        media_error = statistics.mean(errores_finales)
        desviacion = statistics.stdev(errores_finales) if n > 1 else 0.0
        rmse = math.sqrt(sum(errores_cuadraticos) / n)
        media_tiempo = statistics.mean(tiempos_asentamiento)

        # Imprimir en consola para copiar al documento
        print(f"\n" + "="*40)
        print(f"RESULTADOS ACADÉMICOS PARA: {clave_grupo}") # <--- NUEVO
        print(f"Número de iteraciones (n): {n}")
        print(f"Error Medio Estacionario:  {media_error:.2f} px")
        print(f"Desviación Típica (σ):     ±{desviacion:.2f} px")
        print(f"Raíz del Error Cuadrático Medio (RMSE): {rmse:.2f} px")
        print(f"Tiempo Medio de Maniobra:  {media_tiempo:.2f} s")
        print("="*40 + "\n")

        # 5. Dibujar el Histograma
        plt.figure(figsize=(8, 5))
        plt.hist(errores_finales, bins=8, color='#3b82f6', edgecolor='black', alpha=0.8)
        
        plt.axvline(media_error, color='#ef4444', linestyle='dashed', linewidth=2, label=f'Media ({media_error:.2f} px)')
        
        # --- NUEVO: Títulos y nombres de archivo dinámicos ---
        plt.title(f'Distribución del Error de Posicionamiento\n{clave_grupo.replace("_", " ")} (n={n})', fontsize=13, fontweight='bold')
        plt.xlabel('Error final respecto al objetivo (píxeles)', fontsize=11)
        plt.ylabel('Frecuencia (Nº de maniobras)', fontsize=11)
        plt.grid(axis='y', linestyle='--', alpha=0.6)
        plt.legend()
        
        nombre_archivo = f'histograma_{clave_grupo}.png'
        plt.savefig(nombre_archivo, dpi=300, bbox_inches='tight')
        print(f"📊 Histograma de alta resolución guardado como '{nombre_archivo}'")
        plt.close() # <-- Buena práctica: cerrar la figura para que no se solapen si hay varias

if __name__ == "__main__":
    analizar_telemetria("telemetria_pid.csv")