#include "TcpClientESP.h"

WiFiClient* TcpClientESP::getClient() {
    return &client;
}


TcpClientESP::TcpClientESP() {
    connected = false;
    lastAttempt = 0;
    retryInterval = 3000; // 3 segundos
}

bool TcpClientESP::isConnected() {
    return client.connected();
}

void TcpClientESP::connectToServer(String ip, int port, String robotId) {

    Serial.print("Intentando conectar a ");
    Serial.print(ip);
    Serial.print(":");
    Serial.println(port);

    if (client.connect(ip.c_str(), port)) {
        connected = true;
        Serial.println("Conectado al servidor TCP");

        String hello = "{\"type\":\"HELLO\",\"robot_id\":\"" + robotId + "\"}\n";
        client.print(hello);

        Serial.println("HELLO enviado");
    } else {
        connected = false;
        Serial.println("Error al conectar");
    }
}

void TcpClientESP::step(String ip, int port, String robotId) {

    if (client.connected()) {
        connected = true;
        return;
    }

    connected = false;

    if (millis() - lastAttempt >= retryInterval) {
        lastAttempt = millis();
        connectToServer(ip, port, robotId);
    }
}