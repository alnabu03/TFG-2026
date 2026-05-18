import json
import socket
import time


class TcpServer:

    def __init__(self):
        self.sock = None
        self.connected = False
        self.clients = {}
        self.pending_clients = {}
        self.next_client_id = 1
        self.hello_timeout_s = 2.0

    def levantar_servidor(self, host: str, port: int) -> bool:
        if self.connected:
            return True
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind((host, port))
            s.listen(5)
            s.setblocking(False)   # IMPORTANTE: no bloqueante para la GUI

            self.sock = s
            print(f"Servidor escuchando en {host}:{port}")
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self.connected = True
            return True

        except OSError as e:
            print(f"Error al levantar servidor TCP: {e}")
            self.sock = None
            self.connected = False
            return False

    def aceptar(self):
        if not self.sock:
            return

        self._procesar_pendientes()

        try:
            client_socket, address = self.sock.accept()
            print(f"Cliente conectado desde {address}")

            # Ponemos también el cliente en no bloqueante
            client_socket.setblocking(False)

            client_id_temporal = self.next_client_id
            self.clients[client_id_temporal] = client_socket

            try:
                client_socket.send(b"Bienvenido a mi servidor tcp!\n")
            except OSError:
                pass
            except OSError as e: # <-- NUEVO: Escudo anticaídas
                print(f"Error puntual en accept (ignorado): {e}")

            self.pending_clients[client_id_temporal] = time.monotonic()
            self.next_client_id += 1

        except BlockingIOError:
            # No hay conexiones pendientes, y eso está bien
            pass

    def _procesar_pendientes(self):
        ahora = time.monotonic()
        for client_key in list(self.pending_clients.keys()):
            robot_id = self.get_id(client_key)
            if robot_id is not None:
                self.actualizar_diccionario_clientes(robot_id, client_key)
                del self.pending_clients[client_key]
                continue

            if (ahora - self.pending_clients[client_key]) > self.hello_timeout_s:
                print(f"Timeout esperando HELLO del cliente temporal {client_key}")
                try:
                    self.clients[client_key].close()
                except OSError:
                    pass
                self.pending_clients.pop(client_key, None)
                self.clients.pop(client_key, None)

    def get_id(self, client_key):
        if not hasattr(self, 'hello_buffers'):
            self.hello_buffers = {}
            
        if client_key not in self.hello_buffers:
            self.hello_buffers[client_key] = ""
            
        try:
            data = self.clients[client_key].recv(2048)
            if not data:
                return None # Cliente desconectado
                
            text = data.decode("utf-8")
            self.hello_buffers[client_key] += text
            
            # Solo intentamos parsear si hemos recibido el salto de línea completo
            if "\n" in self.hello_buffers[client_key]:
                mensaje_completo = self.hello_buffers[client_key].strip()
                message = json.loads(mensaje_completo)
                
                # Limpiamos el buffer
                del self.hello_buffers[client_key]
                return message["robot_id"]
                
            return None # Aún no ha llegado el mensaje entero
            
        except BlockingIOError:
            return None
        except (json.JSONDecodeError, KeyError, OSError) as e:
            print(f"Error leyendo HELLO del cliente: {e}")
            self.hello_buffers.pop(client_key, None) # Limpiamos en caso de error
            return None

        except BlockingIOError:
            return None
        except (json.JSONDecodeError, KeyError, OSError) as e:
            print(f"Error leyendo HELLO del cliente: {e}")
            return None

    def actualizar_diccionario_clientes(self, robot_id: str, client_key):
        if robot_id in self.clients:
            print(f"Reconexión de {robot_id}: reemplazando socket anterior")
            self.eliminar_cliente(robot_id)
        self.clients[robot_id] = self.clients[client_key]
        del self.clients[client_key]
        print(f"Cliente registrado como {robot_id}")

    def enviar_mensaje(self, mensaje: str):
        self.mostrar_clientes()

        for client_id, client_socket in list(self.clients.items()):
            # Solo enviamos a robots reales, no a claves temporales numéricas
            if isinstance(client_id, int):
                continue

            try:
                client_socket.send((mensaje + "\n").encode("utf-8"))
                print(f"Mensaje enviado al cliente {client_id}: {mensaje}")
            except OSError as e:
                print(f"Error al enviar a {client_id}: {e}")
                self.eliminar_cliente(client_id)

    def leer_mensajes(self):
        mensajes_recibidos = []
        
        # 1. Creamos el diccionario global de buffers si no existe
        if not hasattr(self, 'client_buffers'):
            self.client_buffers = {}

        for client_id, client_socket in list(self.clients.items()):
            if isinstance(client_id, int):
                continue
                
            # 2. Inicializamos el buffer vacío para clientes nuevos
            if client_id not in self.client_buffers:
                self.client_buffers[client_id] = ""

            try:
                data = client_socket.recv(2048)
                if data:
                    texto = data.decode("utf-8")
                    self.client_buffers[client_id] += texto
                    
                    # 3. Solo procesamos si ha llegado el delimitador (\n)
                    if "\n" in self.client_buffers[client_id]:
                        # Separamos todo lo recibido por saltos de línea
                        lineas = self.client_buffers[client_id].split("\n")
                        
                        # El último fragmento de 'lineas' es lo que va después del último '\n'.
                        # Si el mensaje estaba completo, será "". Si estaba a medias, será el resto.
                        # Lo sacamos de la lista y lo devolvemos al buffer para la próxima vuelta.
                        self.client_buffers[client_id] = lineas.pop() 
                        
                        for linea in lineas:
                            if linea.strip():
                                mensajes_recibidos.append((client_id, linea.strip()))
                else:
                    print(f"Cliente {client_id} desconectado")
                    self.eliminar_cliente(client_id)
                    self.client_buffers.pop(client_id, None) # Limpiamos memoria
                    
            except BlockingIOError:
                pass
            except OSError as e:
                print(f"Error al leer de {client_id}: {e}")
                self.eliminar_cliente(client_id)
                self.client_buffers.pop(client_id, None) # Limpiamos memoria
                
        return mensajes_recibidos

    def enviar_a_robot(self, robot_id: str, mensaje: str):
        if robot_id not in self.clients:
            print(f"El robot {robot_id} no está conectado")
            return False

        try:
            self.clients[robot_id].send((mensaje + "\n").encode("utf-8"))
            print(f"Mensaje enviado a {robot_id}: {mensaje}")
            return True
        except OSError as e:
            print(f"Error al enviar a {robot_id}: {e}")
            self.eliminar_cliente(robot_id)
            return False

    def mostrar_clientes(self):
        print(f"Clientes registrados en TCP: {list(self.clients.keys())}")

    def eliminar_cliente(self, robot_id):
        if robot_id in self.clients:
            try:
                self.clients[robot_id].close()
            except OSError:
                pass
            del self.clients[robot_id]
            print(f"Cliente {robot_id} eliminado")
