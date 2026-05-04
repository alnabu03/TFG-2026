import csv
import math
import matplotlib.pyplot as plt

def generar_graficas(archivo_csv):
    # Diccionario para guardar los datos separados por cada robot
    datos_por_robot = {}
    
    try:
        # Leer los datos guardados por tu servidor
        with open(archivo_csv, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                robot = row['robot']
                t = float(row['tiempo'])
                dx = float(row['x_obj']) - float(row['x_act'])
                dy = float(row['y_obj']) - float(row['y_act'])
                
                # Matemáticas correctas para el error de distancia (Teorema de Pitágoras)
                error_d = math.sqrt(dx**2 + dy**2) 
                
                # Si es la primera vez que vemos a este robot, le creamos su espacio
                if robot not in datos_por_robot:
                    datos_por_robot[robot] = {'tiempos': [], 'errores_dist': []}
                
                datos_por_robot[robot]['tiempos'].append(t)
                datos_por_robot[robot]['errores_dist'].append(error_d)
                
    except FileNotFoundError:
        print(f"Error: No se encuentra el archivo {archivo_csv}. ¡Mueve primero el robot!")
        return

    if not datos_por_robot:
        print("El archivo CSV está vacío.")
        return

    # --- DIBUJAR LA GRÁFICA ACADÉMICA ---
    plt.figure(figsize=(10, 5))
    
    # Dibujamos una línea por cada robot que haya participado
    for robot, datos in datos_por_robot.items():
        if not datos['tiempos']: 
            continue
            
        # Normalizar el tiempo para que cada robot empiece en el segundo 0
        t0 = datos['tiempos'][0]
        tiempos_normalizados = [t - t0 for t in datos['tiempos']]
        
        plt.plot(tiempos_normalizados, datos['errores_dist'], label=f'Error Distancia ({robot})', linewidth=2)
    
    # Línea del umbral de aparcamiento
    plt.axhline(y=10, color='r', linestyle='--', label='Umbral Fase 2 (10px)') 
    
    plt.title('Evolución del Error de Distancia - Control PID Multirrobot', fontsize=14)
    plt.xlabel('Tiempo (segundos)', fontsize=12)
    plt.ylabel('Distancia al objetivo (píxeles)', fontsize=12)
    plt.grid(True, linestyle=':', alpha=0.7)
    plt.legend()
    
    # Guardar imagen perfecta para LaTeX
    plt.savefig('grafica_distancia_multirrobot.png', dpi=300, bbox_inches='tight')
    print("¡Gráfica guardada como grafica_distancia_multirrobot.png lista para LaTeX!")
    plt.show()

if __name__ == "__main__":
    generar_graficas("telemetria_pid.csv")