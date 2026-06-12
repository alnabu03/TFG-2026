#ifndef ROBOT_CONTROLLER_H
#define ROBOT_CONTROLLER_H

#include <Arduino.h>

class RobotController {
private:
    int velocidad;

public:
    RobotController(int vel = 50);

    void begin();

    void avanzar();
    void retroceder();
    void girarIzquierda();
    void girarDerecha();
    void parar();
    void moverVelocidades(int VelIzquierda, int VelDerecha);

};

#endif