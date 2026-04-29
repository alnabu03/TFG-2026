#ifndef COMMAND_HANDLER_ESP_H
#define COMMAND_HANDLER_ESP_H

#include <WiFi.h>
#include "RobotController.h"

class CommandHandlerESP {
private:
    struct ScheduledCommand {
        String command;
        unsigned long long startEpochMs;
        unsigned long long stopEpochMs;
    };

    static const uint8_t MAX_SCHEDULED_COMMANDS = 16;

    WiFiClient* client;
    const char* robotId;
    RobotController* robot;
    String buffer;
    ScheduledCommand scheduledQueue[MAX_SCHEDULED_COMMANDS];
    uint8_t scheduledQueueHead;
    uint8_t scheduledQueueTail;
    uint8_t scheduledQueueCount;
    bool activeDurationCommand;
    unsigned long long activeStopEpochMs;
    unsigned long stopAtLocalMs;
    bool useLocalStopTimer;
    bool ntpInitialized;
    bool modoPidActivo;
    float x_act, y_act, th_act;
    float x_obj, y_obj, th_obj;
    unsigned long ultimoTiempoPid;
    unsigned long ultimoMensajePidMs;

    bool encolarComandoProgramado(const ScheduledCommand& cmd);
    bool desencolarComandoProgramado(ScheduledCommand* outCmd);
    bool verPrimerComandoProgramado(ScheduledCommand* outCmd) const;
    

public:
    CommandHandlerESP(WiFiClient* tcpClient, const char* robotId, RobotController* robot);

    void step();
    void procesarMensaje(String mensaje);
    void ejecutarComando(String comando);
    bool esComandoParaMi(String mensaje);
    bool esComandoProgramadoParaMi(const String& mensaje);
    bool programarComando(const String& mensaje);
    void procesarComandoProgramado();
    unsigned long long currentEpochMillis() const;
    void initNtpIfNeeded();
    void calcularYEjecutarPID();
};

#endif
