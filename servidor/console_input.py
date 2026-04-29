import socket, json


def leer_consola(cola):
    print("Hilo de consola arrancado")
    while True:
        mensaje = input ("Escribe un mensaje para enviar al cliente: \n")
        cola.put(mensaje)