import cv2
import numpy as np #Esta librería es para manejar matrices, que es lo que se obtiene al procesar una imagen
import math

#1. Configuramos la cámara, pongo (1) porque voy a usar la cámara de ivcam desde el móvil
cap = cv2.VideoCapture(1)
#2. Cargamos el diccionario de Aruco, uso el de 4x4 con 50 marcadores, pero hay otros tipos de diccionarios disponibles
aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
aruco_params = cv2.aruco.DetectorParameters()

detector = cv2.aruco.ArucoDetector(aruco_dict, aruco_params)

print("Iniciando detección de Aruco. Presiona 'q' para salir.")

while True: 
    ret, frame = cap.read() #cap read nos devuelve un booleano (ret) y el frame capturado.
    if not ret:
        print("No se pudo capturar el video")
        break
    #Convertimos a escala de grises, asi mejoramos la detección.
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    #3. Detectamos los marcadores
    corners, ids, rejected = detector.detectMarkers(gray) #rejected es para ver los contornos que se detectaron pero no se consideraron marcadores válidos, como un negro en el suelo al intentar detectar un marcador.
    if ids is not None: 
        #Dibujamos el cuadfrado alrededor de los marcadores detectados.
        cv2.aruco.drawDetectedMarkers(frame, corners, ids)
        for i in range(len(ids)):
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
            #---Dibujamos los datos en la pantalla:---
            # Punto cental
            cv2.circle(frame, (center_x, center_y), 5, (0, 0, 255), -1)
            #DIbujamos la línea de dirección (la "nariz" del robot)
            cv2.line(frame, (center_x, center_y), (int(front_x), int(front_y)), (0, 255, 0), 2)
            #Mostramos el ID, y los datos (X,Y,Theta)
            texto = f"ID: {ids[i][0]} X: {center_x} Y: {center_y} Theta: {theta_deg}"
            cv2.putText(frame, texto, (center_x - 50, center_y - 20), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
            #Mostramos la imagen
    cv2.imshow("Aruco Detection", frame)
    key = cv2.waitKey(1) & 0xFF
    #Para salir con la letra q
    if key == ord('q'):
        break
cap.release()
cv2.destroyAllWindows()
