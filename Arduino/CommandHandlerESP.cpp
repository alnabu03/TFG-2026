#include "CommandHandlerESP.h"
#include <Arduino.h>
#include <stdlib.h>
#include <time.h>
#include <sys/time.h>

CommandHandlerESP::CommandHandlerESP(WiFiClient* tcpClient, const char* robotId, RobotController* robot) {
    this->client = tcpClient;
    this->robotId = robotId;
    this->robot = robot;
    this->buffer = "";
    this->scheduledQueueHead = 0;
    this->scheduledQueueTail = 0;
    this->scheduledQueueCount = 0;
    this->activeDurationCommand = false;
    this->activeStopEpochMs = 0;
    this->stopAtLocalMs = 0;
    this->useLocalStopTimer = false;
    this->ntpInitialized = false;
    this->modoPidActivo = false;
    this->ultimoTiempoPid = 0;
}

void CommandHandlerESP::step() {
    initNtpIfNeeded();

    if (client == nullptr) {
        procesarComandoProgramado();
        return;
    }

    if (!client->connected()) {
        procesarComandoProgramado();
        return;
    }

    while (client->available()) {
        char c = client->read();

        if (c == '\n') {
            buffer.trim();

            if (buffer.length() > 0) {
                Serial.print("Mensaje recibido del servidor: ");
                Serial.println(buffer);

                procesarMensaje(buffer);
            }

            buffer = "";
        } else {
            buffer += c;
        }
    }

    procesarComandoProgramado();
    if (modoPidActivo) {
        calcularYEjecutarPID();
    }
}

void CommandHandlerESP::procesarMensaje(String mensaje) {
    if (esComandoProgramadoParaMi(mensaje)) {
        if (!programarComando(mensaje)) {
            Serial.println("No se pudo programar el comando recibido.");
        }
    } else if (esComandoParaMi(mensaje)) {
        ejecutarComando(mensaje);
    } else {
        Serial.println("Mensaje recibido, pero no es una orden para este robot.");
    }
}

bool CommandHandlerESP::esComandoParaMi(String mensaje) {
    String id = String(robotId);

    if (mensaje == id + " AVANZA") return true;
    if (mensaje == id + " RETROCEDE") return true;
    if (mensaje == id + " IZQUIERDA") return true;
    if (mensaje == id + " DERECHA") return true;
    if (mensaje == id + " PARA") return true;
    if(mensaje == id + " PID_DATA") return true;

    return false;
}

bool CommandHandlerESP::esComandoProgramadoParaMi(const String& mensaje) {
    String id = String(robotId);
    String prefijo = id + " EXEC_AT_MS ";
    return mensaje.startsWith(prefijo);
}

bool CommandHandlerESP::programarComando(const String& mensaje) {
    String id = String(robotId);
    String prefijo = id + " EXEC_AT_MS ";
    if (!mensaje.startsWith(prefijo)) {
        return false;
    }

    String resto = mensaje.substring(prefijo.length());
    int primerEspacio = resto.indexOf(' ');
    if (primerEspacio < 0) {
        return false;
    }

    String epochMsTexto = resto.substring(0, primerEspacio);
    unsigned long long startEpochMs = strtoull(epochMsTexto.c_str(), nullptr, 10);
    if (startEpochMs == 0) {
        return false;
    }

    resto = resto.substring(primerEspacio + 1);
    resto.trim();

    unsigned long duracionMs = 0;
    int idxDur = resto.indexOf(" DUR_MS ");
    String comando = resto;
    if (idxDur >= 0) {
        comando = resto.substring(0, idxDur);
        String durTexto = resto.substring(idxDur + 8);
        durTexto.trim();
        duracionMs = strtoul(durTexto.c_str(), nullptr, 10);
    }
    comando.trim();

    if (
        comando != "AVANZA" &&
        comando != "RETROCEDE" &&
        comando != "IZQUIERDA" &&
        comando != "DERECHA" &&
        comando != "PARA"
    ) {
        return false;
    }

    ScheduledCommand scheduledCmd;
    scheduledCmd.command = comando;
    scheduledCmd.startEpochMs = startEpochMs;
    scheduledCmd.stopEpochMs = (duracionMs > 0 && comando != "PARA")
        ? (startEpochMs + duracionMs)
        : 0;

    if (!encolarComandoProgramado(scheduledCmd)) {
        Serial.print("Cola de comandos programados llena (max ");
        Serial.print(MAX_SCHEDULED_COMMANDS);
        Serial.println(").");
        return false;
    }

    Serial.print("Comando programado: ");
    Serial.print(scheduledCmd.command);
    Serial.print(" @ ");
    Serial.print((unsigned long)scheduledCmd.startEpochMs);
    if (scheduledCmd.stopEpochMs > 0) {
        Serial.print(" hasta ");
        Serial.print((unsigned long)scheduledCmd.stopEpochMs);
    }
    Serial.print(" | en cola: ");
    Serial.print(scheduledQueueCount);
    Serial.println();
    return true;
}

void CommandHandlerESP::procesarComandoProgramado() {
    unsigned long long nowMs = currentEpochMillis();

    if (activeDurationCommand && nowMs > 0 && nowMs >= activeStopEpochMs) {
        robot->parar();
        activeDurationCommand = false;
        activeStopEpochMs = 0;
    }

    if (useLocalStopTimer && ((long)(millis() - stopAtLocalMs) >= 0)) {
        robot->parar();
        useLocalStopTimer = false;
        stopAtLocalMs = 0;
    }

    ScheduledCommand nextCmd;
    if (!verPrimerComandoProgramado(&nextCmd)) {
        return;
    }

    if (nowMs > 0) {
        if (nowMs < nextCmd.startEpochMs) {
            return;
        }

        if (!desencolarComandoProgramado(&nextCmd)) {
            return;
        }
        activeDurationCommand = false;
        activeStopEpochMs = 0;
        ejecutarComando(String(robotId) + " " + nextCmd.command);
        if (nextCmd.stopEpochMs > nextCmd.startEpochMs) {
            activeDurationCommand = true;
            activeStopEpochMs = nextCmd.stopEpochMs;
        }
        return;
    }

    // Fallback: sin tiempo NTP válido, ejecutar de inmediato.
    if (!desencolarComandoProgramado(&nextCmd)) {
        return;
    }
    activeDurationCommand = false;
    activeStopEpochMs = 0;
    ejecutarComando(String(robotId) + " " + nextCmd.command);
    if (nextCmd.stopEpochMs > nextCmd.startEpochMs) {
        unsigned long dur = (unsigned long)(nextCmd.stopEpochMs - nextCmd.startEpochMs);
        stopAtLocalMs = millis() + dur;
        useLocalStopTimer = true;
    }
}

unsigned long long CommandHandlerESP::currentEpochMillis() const {
    struct timeval tv;
    if (gettimeofday(&tv, nullptr) != 0) {
        return 0;
    }
    if (tv.tv_sec < 100000) {
        return 0;
    }
    return (unsigned long long)tv.tv_sec * 1000ULL + (unsigned long long)(tv.tv_usec / 1000ULL);
}

void CommandHandlerESP::initNtpIfNeeded() {
    if (ntpInitialized || WiFi.status() != WL_CONNECTED) {
        return;
    }
    configTime(0, 0, "pool.ntp.org", "time.nist.gov", "time.google.com");
    ntpInitialized = true;
    Serial.println("Sincronización NTP inicializada.");
}

bool CommandHandlerESP::encolarComandoProgramado(const ScheduledCommand& cmd) {
    if (scheduledQueueCount >= MAX_SCHEDULED_COMMANDS) {
        return false;
    }

    scheduledQueue[scheduledQueueTail] = cmd;
    scheduledQueueTail = (scheduledQueueTail + 1) % MAX_SCHEDULED_COMMANDS;
    scheduledQueueCount++;
    return true;
}

bool CommandHandlerESP::desencolarComandoProgramado(ScheduledCommand* outCmd) {
    if (scheduledQueueCount == 0) {
        return false;
    }

    if (outCmd != nullptr) {
        *outCmd = scheduledQueue[scheduledQueueHead];
    }
    scheduledQueueHead = (scheduledQueueHead + 1) % MAX_SCHEDULED_COMMANDS;
    scheduledQueueCount--;
    return true;
}

bool CommandHandlerESP::verPrimerComandoProgramado(ScheduledCommand* outCmd) const {
    if (scheduledQueueCount == 0) {
        return false;
    }
    if (outCmd != nullptr) {
        *outCmd = scheduledQueue[scheduledQueueHead];
    }
    return true;
}

void CommandHandlerESP::ejecutarComando(String comando) {
    String id = String(robotId);

    if (comando == id + " AVANZA") {
        Serial.println("ORDEN RECIBIDA: AVANZAR");
        robot->avanzar();
    }
    else if (comando == id + " RETROCEDE") {
        Serial.println("ORDEN RECIBIDA: RETROCEDER");
        robot->retroceder();
    }
    else if (comando == id + " IZQUIERDA") {
        Serial.println("ORDEN RECIBIDA: IZQUIERDA");
        robot->girarIzquierda();
    }
    else if (comando == id + " DERECHA") {
        Serial.println("ORDEN RECIBIDA: DERECHA");
        robot->girarDerecha();
    }
    else if (comando == id + " PARA") {
        Serial.println("ORDEN RECIBIDA: PARAR");
        robot->parar();
        modoPidActivo = false;
    }
    else if (comando.startsWith(id + "PID_DATA")) { //esta funcion hace lo que hace split() en python, elimina espacios al principio y al final
        String data = comando.substring(id.length() + 10);
        data.trim();
        
        int partes [6];
        int idx = 0;
        int from = 0;
        int to = data.indexOf(' ');
        String tokens[6];

        while (to != -1 && idx < 5) {
            tokens[idx++] = data.substring(from, to);
            from = to + 1;
            to = data.indexOf(' ', from);
        }
        tokens[idx] = data.substring(from);
        if (idx == 5) {
            x_act = tokens[0].toFloat();
            y_act = tokens[1].toFloat();
            th_act = tokens[2].toFloat();
            x_obj = tokens[3].toFloat();
            y_obj = tokens[4].toFloat();
            th_obj = tokens[5].toFloat();
            modoPidActivo = true;
            if (ultimoTiempoPid == 0) {
                ultimoMensajePidsMs = millis();
            }
        } else {
            Serial.println("Datos PID mal formateados: " + data);
        }
    }
    else {
        Serial.print("Comando no reconocido: ");
        Serial.println(comando);
    }

}

void CommandHandlerESP::calcularYEjecutarPID(){
    if (millis() - ultimoMensajePidsMs > 1000){
        robot->parar();
        modoPidActivo = false;
        Serial.println("No se han recibido datos PID en el último segundo, deteniendo robot por seguridad.");
        return;
    }
    unsigned long ahora = millis();
    float dt = (ahora - ultimoTiempoPid) / 1000.0;
    if(dt <= 0) return;
    ultimoTiempoPid = ahora;

    float dx = x_obj - x_act;
    float dy = y_obj - y_act;
    float error_dist = sqrt(dx*dx + dy*dy);
    if (error_dist < 20.0)){
        robot->parar();
        modoPidActivo = false;
        Serial.println("Objetivo alcanzado, deteniendo robot.");
        return;
    }

    float angulo_objetivo_rad = atan2(-dy,dx);
    float angulo_actual_rad = th_act * PI / 180.0;
    float error_ang = angulo_objetivo_rad - angulo_actual_rad;
    error_ang = atan2(sin(error_ang), cos(error_ang)); // Normalizar a [-pi, pi]
    //Ajustes del PID (podemos jugar con estos valores)
    float kp_dist = 0.5; //Potencia de avance (el maqueen tiene de 0 a 255)
    float kp_ang = 60; //Potencia de giro

    float velocidad_avancce = kp_dist * error_dist;
    float velocidad_giro = kp_ang * error_ang;
    if (abs(error_ang) > PI / 4) {
        velocidad_avancce = 0; // Si el error angular es mayor de 45, solo giramos
    }
    float vel_izquierda = velocidad_avancce - velocidad_giro;
    float vel_derecha = velocidad_avancce + velocidad_giro;
    //limitamos velocidades al rango del maqueen (0 a 255)
    if (vel_izquierda > 255) vel_izquierda = 255;
    if (vel_izquierda < -255) vel_izquierda = -255;
    if (vel_derecha > 255) vel_derecha = 255;
    if (vel_derecha < -255) vel_derecha = -255; 

    robot->moverVelocidades((int)vel_izquierda, (int)vel_derecha);

}
