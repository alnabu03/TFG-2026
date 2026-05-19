#include "RobotController.h"
#include <Wire.h>

#define MAQUEEN_I2C_ADDR 0x10

RobotController::RobotController(int vel) {
    velocidad = vel;
}

void RobotController::begin() {
    Wire.begin();  // Inicializa I2C
    Serial.println("RobotController listo");
}

// Función interna para hablar con el hardware I2C
void setMotor(uint8_t motor, uint8_t direccion, uint8_t velocidad) {
    Wire.beginTransmission(MAQUEEN_I2C_ADDR);
    Wire.write(motor);
    Wire.write(direccion);
    Wire.write(velocidad);
    Wire.endTransmission();
}

void RobotController::moverVelocidades(int velIzquierda, int velDerecha) {
    // Motor izquierdo (0)
    // Direccion: 0 = adelante, 1 = atrás
    uint8_t dirIzquierda = (velIzquierda >= 0) ? 0 : 1; 
    uint8_t pwmIzquierda = abs(velIzquierda);
    if (pwmIzquierda > 255) pwmIzquierda = 255; // Límite de seguridad de hardware

    // Motor derecho (2)
    uint8_t dirDerecha = (velDerecha >= 0) ? 0 : 1;
    uint8_t pwmDerecha = abs(velDerecha);
    if (pwmDerecha > 255) pwmDerecha = 255;     // Límite de seguridad de hardware

    setMotor(0, dirIzquierda, pwmIzquierda);
    setMotor(2, dirDerecha, pwmDerecha);
}

// MOVIMIENTOS BÁSICOS 

void RobotController::avanzar() {
    Serial.println("AVANZANDO");
    moverVelocidades(velocidad, velocidad);
}

void RobotController::retroceder() {
    Serial.println("RETROCEDIENDO");
    moverVelocidades(-velocidad, -velocidad);
}

void RobotController::girarIzquierda() {
    Serial.println("GIRO IZQUIERDA");
    moverVelocidades(-velocidad, velocidad);
}

void RobotController::girarDerecha() {
    Serial.println("GIRO DERECHA");
    moverVelocidades(velocidad, -velocidad);
}

void RobotController::parar() {
    Serial.println("PARADO");
    moverVelocidades(0, 0);
}