import cv2
import numpy as np #Esta librería es para manejar matrices, que es lo que se obtiene al procesar una imagen
import math

def detectar_poses_robot(frame,detector):
    #Convertimos a escala de grises, asi mejoramos la detección.
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    #3. Detectamos los marcadores
    corners, ids, rejected = detector.detectMarkers(gray) #rejected es para ver los contornos que se detectaron pero no se consideraron marcadores válidos, como un negro en el suelo al intentar detectar un marcador.
    poses = {}
    if ids is not None: 
        #Dibujamos el cuadfrado alrededor de los marcadores detectados.
        cv2.aruco.drawDetectedMarkers(frame, corners, ids)
        for i in range(len(ids)):
            marker_id = ids[i][0]
            #Vamos a obtener las esquinas:
            #El orden de OpenCV nos da: top-left, top-right, bottom-right, bottom-left
            c = corners[i][0] #ponemos dos corchetes porque corners es una lista de listas
            tl, tr, br, bl = c[0], c[1], c[2], c[3]
            #---Ahora calculamos el centro (x,y)---
            center_x = int((tl[0]+tr[0]+br[0]+bl[0])/4)
            center_y = int((tl[1]+tr[1]+br[1]+bl[1])/4)
            #---Ahora calculamos el ángulo theta---#
            front_x = ((tl[0]+tr[0])/2)
            front_y = ((tl[1]+tr[1])/2)
            #Diferencia entre el frente y el centro
            dx = front_x - center_x
            dy = front_y - center_y
            #Calculamos el ángulo en radianes usando atan2.
            #En OpenCV, la coordenada Y crece hacia abajo, así que invertimos dy si queremos el ángulo matemático estándar
            theta_rad = math.atan2(-dy, dx)
            theta_deg = math.degrees(theta_rad)
            poses[marker_id] = {
                "x": center_x,
                "y": center_y,
                "theta": theta_deg
            }
            #---Dibujamos los datos en la pantalla:---
            # Punto cental
            cv2.circle(frame, (center_x, center_y), 5, (0, 0, 255), -1)
            #DIbujamos la línea de dirección (la "nariz" del robot)
            cv2.line(frame, (center_x, center_y), (int(front_x), int(front_y)), (0, 255, 0), 2)
            #Mostramos el ID, y los datos (X,Y,Theta)
            texto = f"ID: {ids[i][0]} X: {center_x} Y: {center_y} Theta: {theta_deg}"
            cv2.putText(frame, texto, (center_x - 50, center_y - 20), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
    return poses, frame
