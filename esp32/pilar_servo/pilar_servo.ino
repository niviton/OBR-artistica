/*
  Pilar do cenário — ESP32 + 1 servo motor
  ----------------------------------------
  Recebe o ângulo por Bluetooth BLE (Wi-Fi é proibido na OBR) e gira o pilar
  suavemente para a posição da cena:

      0°   -> portão     (cena 2)
      90°  -> menino     (cena 3)
      180° -> castelo    (cena 1)

  Ligações:
      Servo sinal (laranja/amarelo) -> GPIO 13
      Servo VCC (vermelho)          -> 5V de uma fonte/bateria externa (não use o 3V3 do ESP32)
      Servo GND (marrom/preto)      -> GND da fonte E GND do ESP32 (terra em comum!)

  Bibliotecas (Arduino IDE > Gerenciador de Bibliotecas):
      - ESP32Servo (Kevin Harrington)
  Placa: "ESP32 Dev Module" (pacote esp32 da Espressif).

  Protocolo: o notebook escreve um texto com o ângulo ("0", "90" ou "180")
  na característica CHAR_UUID. O ESP32 responde por notificação "OK <ângulo>".
  Também aceita o mesmo comando pelo Monitor Serial (115200), para testes.
*/

#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLE2902.h>
#include <ESP32Servo.h>

// ---------------------------------------------------------------- configuração
#define NOME_BLE      "PilarCastelo"     // o Python procura por este nome
#define SERVICE_UUID  "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
#define CHAR_UUID     "6e400002-b5a3-f393-e0a9-e50e24dcca9e"

const int PINO_SERVO      = 13;
const int ANGULO_INICIAL  = 180;   // começa virado para o castelo (cena 1)
const int MS_POR_GRAU     = 12;    // velocidade: 12 ms/grau = 90° em ~1,1 s
const int PULSO_MIN_US    = 500;   // ajuste se seu servo não chegar a 0°/180°
const int PULSO_MAX_US    = 2400;
const int PINO_LED        = 2;     // LED da placa: aceso = notebook conectado

// ---------------------------------------------------------------- estado
Servo servo;
BLECharacteristic *caracteristica = nullptr;
volatile int alvo = ANGULO_INICIAL;
int atual = ANGULO_INICIAL;
bool conectado = false;
unsigned long ultimoPasso = 0;

void definirAlvo(int angulo) {
  angulo = constrain(angulo, 0, 180);
  alvo = angulo;
  Serial.printf("Novo alvo: %d graus\n", angulo);
  if (caracteristica && conectado) {
    String resposta = "OK " + String(angulo);
    caracteristica->setValue(resposta.c_str());
    caracteristica->notify();
  }
}

// Converte o texto recebido ("90", "90\n", " 180 ") em ângulo
bool lerAngulo(String texto, int &angulo) {
  texto.trim();
  if (texto.length() == 0) return false;
  for (unsigned int i = 0; i < texto.length(); i++) {
    if (!isDigit(texto[i])) return false;
  }
  angulo = texto.toInt();
  return angulo >= 0 && angulo <= 180;
}

// ---------------------------------------------------------------- BLE
class EventosServidor : public BLEServerCallbacks {
  void onConnect(BLEServer *s) override {
    conectado = true;
    digitalWrite(PINO_LED, HIGH);
    Serial.println("Notebook conectado");
  }
  void onDisconnect(BLEServer *s) override {
    conectado = false;
    digitalWrite(PINO_LED, LOW);
    Serial.println("Notebook desconectado — anunciando de novo");
    BLEDevice::startAdvertising();   // permite reconectar sozinho
  }
};

class EventosEscrita : public BLECharacteristicCallbacks {
  void onWrite(BLECharacteristic *c) override {
    String recebido = String(c->getValue().c_str());
    int angulo;
    if (lerAngulo(recebido, angulo)) {
      definirAlvo(angulo);
    } else {
      Serial.printf("Comando ignorado: '%s'\n", recebido.c_str());
    }
  }
};

void iniciarBLE() {
  BLEDevice::init(NOME_BLE);
  BLEServer *servidor = BLEDevice::createServer();
  servidor->setCallbacks(new EventosServidor());
  BLEService *servico = servidor->createService(SERVICE_UUID);
  caracteristica = servico->createCharacteristic(
      CHAR_UUID,
      BLECharacteristic::PROPERTY_WRITE | BLECharacteristic::PROPERTY_WRITE_NR |
      BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_NOTIFY);
  caracteristica->addDescriptor(new BLE2902());
  caracteristica->setCallbacks(new EventosEscrita());
  caracteristica->setValue(String(ANGULO_INICIAL).c_str());
  servico->start();
  BLEAdvertising *anuncio = BLEDevice::getAdvertising();
  anuncio->addServiceUUID(SERVICE_UUID);
  anuncio->setScanResponse(true);
  BLEDevice::startAdvertising();
  Serial.println("BLE pronto: " NOME_BLE);
}

// ---------------------------------------------------------------- setup / loop
void setup() {
  Serial.begin(115200);
  pinMode(PINO_LED, OUTPUT);
  servo.setPeriodHertz(50);
  servo.attach(PINO_SERVO, PULSO_MIN_US, PULSO_MAX_US);
  servo.write(atual);
  iniciarBLE();
}

void loop() {
  // movimento suave: 1 grau a cada MS_POR_GRAU, sem travar o BLE
  if (atual != alvo && millis() - ultimoPasso >= (unsigned long)MS_POR_GRAU) {
    ultimoPasso = millis();
    atual += (alvo > atual) ? 1 : -1;
    servo.write(atual);
  }
  // teste pelo Monitor Serial: digite 0, 90 ou 180 e Enter
  if (Serial.available()) {
    int angulo;
    if (lerAngulo(Serial.readStringUntil('\n'), angulo)) definirAlvo(angulo);
  }
}
