#ifndef DISCOVERY_CLIENT_H
#define DISCOVERY_CLIENT_H
#include <WiFiUdp.h>


class DiscoveryClient {
private:
    const char* robotId;
    int udpPort;
    WiFiUDP udp;
    char incomingPacket[256];

public:
    DiscoveryClient(const char* robotId, int udpPort);
    bool begin();
    void step();
};

#endif