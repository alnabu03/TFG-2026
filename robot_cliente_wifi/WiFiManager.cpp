#include "WiFiManager.h"
#include <Arduino.h>

WiFiManager::WiFiManager(const char* ssid, const char* password) {
  this->ssid = "PONER NOMBRE DE LA RED";
  this->password = "PONER CONTRASEÑA DE LA RED";
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
