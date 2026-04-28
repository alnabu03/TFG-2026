#include "WiFiManager.h"
#include "DiscoveryClient.h"
#include "TcpClientESP.h"
#include "CommandHandlerESP.h"
#include "RobotController.h"

TcpClientESP tcpClient;
WiFiManager wifiManager("iPhone", "hola1234");
const char* ROBOT_ID = "EP1";
DiscoveryClient discoveryClient(ROBOT_ID, 37021);
CommandHandlerESP* commandHandler = nullptr;
RobotController robot;

extern String serverIp;
extern int serverTcpPort;
extern bool tcpInfoReady;



void setup() {
  Serial.begin(115200);
  delay(1000);
  robot.begin();
  if (wifiManager.connect()) {
    discoveryClient.begin();
  }
  commandHandler = new CommandHandlerESP(tcpClient.getClient(), ROBOT_ID, &robot);
}

void loop() {

  discoveryClient.step();

  if (tcpInfoReady) {
    tcpClient.step(serverIp, serverTcpPort, ROBOT_ID);
  }

  if (commandHandler != nullptr) {
    commandHandler->step();
  }
}
