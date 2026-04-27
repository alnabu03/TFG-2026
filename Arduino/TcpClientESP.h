#ifndef TCP_CLIENT_ESP_H
#define TCP_CLIENT_ESP_H

#include <WiFi.h>

WiFiClient* getClient();


class TcpClientESP {
private:
    WiFiClient client;
    bool connected;
    unsigned long lastAttempt;
    unsigned long retryInterval;

public:
    TcpClientESP();
    WiFiClient* getClient();
    void connectToServer(String ip, int port, String robotId);
    void step(String ip, int port, String robotId);

    bool isConnected();
};

#endif