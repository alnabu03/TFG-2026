#include "DiscoveryClient.h"
#include <Arduino.h>


String serverIp ="";
int serverTcpPort = 0;
bool tcpInfoReady = false;
DiscoveryClient::DiscoveryClient(const char* robotId, int udpPort) {
  this->robotId = robotId;
  this->udpPort = udpPort;
}

bool DiscoveryClient::begin() {
  if (udp.begin(udpPort)) {
    Serial.print("Discovery UDP escuchando en puerto ");
    Serial.println(udpPort);
    return true;
  } else {
    Serial.println("Error al iniciar discovery UDP");
    return false;
  }
}

void DiscoveryClient::step() {
  int packetSize = udp.parsePacket();

  if (!packetSize) {
    return;
  }

  int len = udp.read(incomingPacket, sizeof(incomingPacket) - 1);
  if (len <= 0) {
    return;
  }

  incomingPacket[len] = '\0';

  String mensaje = String(incomingPacket);
  mensaje.trim();

  Serial.print("UDP recibido: ");
  Serial.println(mensaje);

  bool esDiscover = false;

  if (mensaje == "DISCOVER") {

    serverIp = udp.remoteIP().toString();
    serverTcpPort = 5000;
    Serial.print("Ip del servidor guardada:");
    Serial.println(serverIp);
    
    esDiscover = true;
  }
  else if (mensaje.indexOf("\"type\"") != -1 && mensaje.indexOf("DISCOVER") != -1) {
    serverIp = udp.remoteIP().toString();
    
    // --- ARREGLO BUG 3: Extraer el tcp_port del JSON de forma dinámica ---
    int indexPuerto = mensaje.indexOf("\"tcp_port\":");
    if (indexPuerto != -1) {
        // Saltamos los caracteres de la etiqueta (son 11 espacios)
        int inicioValor = indexPuerto + 11;
        int finValor = mensaje.indexOf("}", inicioValor);
        
        if (finValor != -1) {
            serverTcpPort = mensaje.substring(inicioValor, finValor).toInt();
        } else {
            serverTcpPort = 5000; // Seguridad por si la red corta el paquete
        }
    } else {
        serverTcpPort = 5000; // Fallback
    }
    
    Serial.print("Ip del servidor guardada: ");
    Serial.print(serverIp);
    Serial.print(" | Puerto TCP a conectar: ");
    Serial.println(serverTcpPort);
    
    esDiscover = true;
  }

  if (esDiscover) {
    Serial.println("DISCOVER recibido, respondiendo HERE...");

    String reply = "{\"type\":\"HERE\",\"robot_id\":\"" + String(robotId) + "\"}";

    udp.beginPacket(udp.remoteIP(), udp.remotePort());
    udp.print(reply);
    udp.endPacket();

    Serial.print("Respuesta HERE enviada a ");
    Serial.print(udp.remoteIP());
    Serial.print(":");
    Serial.println(udp.remotePort());
    tcpInfoReady = true;
  }
}