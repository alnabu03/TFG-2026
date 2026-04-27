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

// Función interna para motores
void setMotor(uint8_t motor, uint8_t direccion, uint8_t velocidad) {
    Wire.beginTransmission(MAQUEEN_I2C_ADDR);
    Wire.write(motor);
    Wire.write(direccion);
    Wire.write(velocidad);
    Wire.endTransmission();
}

// Motores:
// motor 0 = izquierdo
// motor 2 = derecho
// direccion: 0 = adelante, 1 = atrás

void RobotController::avanzar() {
    Serial.println("AVANZANDO");

    setMotor(0, 0, velocidad); // izquierda adelante
    setMotor(2, 0, velocidad); // derecha adelante
}

void RobotController::retroceder() {
    Serial.println("RETROCEDIENDO");

    setMotor(0, 1, velocidad);
    setMotor(2, 1, velocidad);
}

void RobotController::girarIzquierda() {
    Serial.println("GIRO IZQUIERDA");

    setMotor(0, 1, velocidad); // izquierda atrás
    setMotor(2, 0, velocidad); // derecha adelante
}

void RobotController::girarDerecha() {
    Serial.println("GIRO DERECHA");

    setMotor(0, 0, velocidad);
    setMotor(2, 1, velocidad);
}

void RobotController::parar() {
    Serial.println("PARADO");

    setMotor(0, 0, 0);
    setMotor(2, 0, 0);
}

void moverVelocidades(int VelIzquierda, int VelDerecha){
    //Motor izquierdo (0)
    if(velIzquierda >= 0){
        setMotor(0, 0, VelIzquierda); // adelante
    } else {
        setMotor(0, 1, -VelIzquierda); // atrás
    }
    //Motor derecho (2)
    if(VelDerecha >= 0){
        setMotor(2, 0, VelDerecha); // adelante
    } else {
        setMotor(2, 1, -VelDerecha); // atrás
    }
}
