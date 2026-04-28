#ifndef WIFI_MANAGER_H
#define WIFI_MANAGER_H

#include <WiFi.h>

class WiFiManager {
  private:
    const char* ssid;
    const char* password;

  public:
    WiFiManager(const char* ssid, const char* password);
    bool connect();
};

#endif