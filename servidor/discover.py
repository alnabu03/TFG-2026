import socket, json, time




class DiscoveryServer:
    def __init__(self):

        self.robots = {} #Diccionario para almacenar los robots detectados, con su ID como clave y la última vez que se les vio como valor. Esto nos permite llevar un registro de los robots activos en la red y detectar cuando alguno se pierde.
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) #Socket UDP para enviar mensajes de descubrimiento y recibir respuestas de los robots. Este socket se configura para enviar mensajes a la dirección de broadcast y para no bloquear el programa mientras espera respuestas.
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.send_period = 5.0 #Cada cuántos segundos se envía un mensaje de descubrimiento. Esto controla la frecuencia con la que el servidor busca nuevos robots en la red.
        self.last_send = 0.0 #Último tiempo en que se envió un mensaje de descubrimiento. Esto se usa para calcular cuándo es el momento de enviar el siguiente mensaje.
        self.ttl = 35.0 #Tiempo en segundos que se considera que un robot
        self.robot_ports = range(37021, 37031) #Rango de puertos en los que los robots escuchan mensajes de descubrimiento. El servidor enviará mensajes a la dirección de broadcast en cada uno de estos puertos para intentar descubrir los robots.
        self.sock.setblocking(False) #Ponemos el socket en modo no bloqueante para que las llamadas a recvfrom() no bloqueen el programa si no hay mensajes disponibles, sino que lancen una excepción que podemos capturar para manejar esa situación.

    def send_discover(self):
        message = {"type": "DISCOVER",
                "ip": "192.168.1.255",
                "tcp_port": 5000}
        data = json.dumps(message).encode('utf-8') #Convertimos el mensaje de descubrimiento a JSON y luego a bytes para enviarlo por la red. El mensaje es un diccionario con una clave "type" que indica que es un mensaje de descubrimiento.
        for port in self.robot_ports:
            self.sock.sendto(data, ('192.168.1.255', port)) #Enviamos el mensaje de descubrimiento a la dirección de broadcast en cada uno de los puertos que los robots están escuchando. Esto permite que cualquier robot en la red que esté escuchando en esos puertos reciba el mensaje y pueda responder.
        print("DISCOVER ENVIADO")
    
    def receive_responses(self):
        while True:
            try:
                data, addr = self.sock.recvfrom(2048)
            except BlockingIOError:
                return

            text = data.decode('utf-8', errors='replace')
            print(f"UDP bruto recibido desde {addr}: {repr(text)}")

            try:
                message = json.loads(text)
                print("Mendaje recibido del robot:", message)
            except Exception as e:
                print("No se pudo parsear JSON:", e)
                continue

            if message.get("type") != "HERE":
                print("No era un HERE")
                continue

            robot_id = message.get("robot_id", "UNKNOWN")
            ip = addr[0]
            self.robots[robot_id] = {
                "ip": ip,
                "last_seen": time.time()
            }
            print(f"ROBOT DETECTADO: {robot_id} en {ip}")

    def remove_inactive_robots(self):
        now = time.time()
        robots_perdidos = []

        for robot_id, info in list(self.robots.items()):
            if now - info['last_seen'] > self.ttl:
                print(f"ROBOT PERDIDO: {robot_id} en {info['ip']}")
                robots_perdidos.append(robot_id)
                del self.robots[robot_id]

        return robots_perdidos

    def step(self):
        now = time.time()
        if now - self.last_send > self.send_period:
            self.send_discover()
            self.last_send = now
        self.receive_responses()
        robots_perdidos = self.remove_inactive_robots()
        return robots_perdidos