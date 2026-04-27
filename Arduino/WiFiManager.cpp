#include "WiFiManager.h"
#include <Arduino.h>

WiFiManager::WiFiManager(const char* ssid, const char* password) {
  //this->ssid = "WiFi_OliveNet-6FA1A5_5G";
  //this->password = "PvJyd53v";

  this->ssid = "iPhone";
  this->password = "hola1234";

  //this->ssid = "MOVISTAR_A4E8";
  //this->password = "MMV7TJTdd44HUUKT3M3M";
}

bool WiFiManager::connect() {
  Serial.println("Iniciando conexion WiFi...");

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  unsigned long inicio = millis();
  const unsigned long timeout = 15000;

  while (WiFi.status() != WL_CONNECTED && millis() - inicio < timeout) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("WiFi conectado correctamente");
    Serial.print("IP local del ESP32: ");
    Serial.println(WiFi.localIP());
    return true;
  } else {
    Serial.println("Fallo al conectar al WiFi");
    return false;
  }
}