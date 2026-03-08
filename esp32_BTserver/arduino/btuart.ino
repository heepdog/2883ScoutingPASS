#include <ArduinoBLE.h>
#include <LittleFS.h>

// Nordic UART Service UUIDs
BLEService             uartService("6E400001-B5A3-F393-E0A9-E50E24DCCA9E");
BLECharacteristic rxCharacteristic("6E400002-B5A3-F393-E0A9-E50E24DCCA9E", BLEWrite | BLEWriteWithoutResponse, 512);
BLECharacteristic txCharacteristic("6E400003-B5A3-F393-E0A9-E50E24DCCA9E", BLERead | BLENotify, 512);

// Binary command definitions
#define CMD_PUT   0x01
#define CMD_END   0x02
#define CMD_GET   0x03
#define CMD_CLEAR 0x04

void handleCommand(const uint8_t* data,  int length);
// void storeDataToFile(String data);
void storeDataToFile(const uint8_t* data, int length);
void sendStoredData();
void clearStoredData();
String uint8_tToString(const uint8_t* data, int length);

bool putMode = false;

void setup() {
  Serial.begin(115200);
  
// Nordic UART Service UUIDs
  Serial.begin(115200);
  
  // Initialize LittleFS
  if (!LittleFS.begin()) {
    Serial.println("LittleFS failed to mount, formatting...");
    LittleFS.format();
    if (!LittleFS.begin()) {
      Serial.println("LittleFS format failed");
    }
  }

  if (!BLE.begin()) {
    Serial.println("BLE Failed");
    while (1);
  }
  
  BLE.setLocalName("ESP32-C3 FRED");
  BLE.setAdvertisedService(uartService);
  uartService.addCharacteristic(rxCharacteristic);
  uartService.addCharacteristic(txCharacteristic);
  BLE.addService(uartService);
  
  rxCharacteristic.writeValue("");
  txCharacteristic.writeValue("");
  
  BLE.advertise();
  Serial.println("Waiting for connection...");
}

void loop() {
  BLEDevice central = BLE.central();

  if (central) {
    Serial.print("Connected to: ");
    Serial.println(central.address());

    while (central.connected()) {
      if (rxCharacteristic.written()) {
        int length = rxCharacteristic.valueLength();        
        uint8_t data[length];
        rxCharacteristic.readValue(data, length);
        String receivedData = uint8_tToString(data, length);

        Serial.print("BLE received: ");
        Serial.print(length);
        Serial.println(receivedData);
        
        handleCommand(data, length);
      }

      if (Serial.available()) {
        String serialData = Serial.readString();
        serialData.trim();
        txCharacteristic.writeValue(serialData.c_str());
        Serial.print("BLE sent: ");
        Serial.println(serialData);
      }
    }

    Serial.print("Disconnected from: ");
    Serial.println(central.address());
  }
}

void handleCommand(const uint8_t* data, int length) {
  if (length == 0) return;
  uint8_t command = data[0];

  switch (command){

    case CMD_PUT:
      putMode = true;
      Serial.println("Entered put mode");
      break;
    case CMD_END:
      if (putMode) {
        putMode = false;
        Serial.println("Exited Put Mode");
      }
      break;
    case CMD_GET:
      sendStoredData();
      Serial.println("Sent data");
      break;
    case CMD_CLEAR:
      clearStoredData();
      Serial.println("Data Cleared");
      break;

    default:
      if (putMode && length > 1){
        //String dataString = uint8_tToString(data, length);
        // String dataString = "";
        // for (int i = 0; i < length; i++){
        //   dataString += (char)data[i];
        // }
        //storeDataToFile(dataString);
        storeDataToFile(data, length);
        Serial.println("Data Stored");
      }
    

  else {
    txCharacteristic.writeValue("Unknown command. Use: Put <data>, Get, or Clear");
    Serial.println("Recieved Unknown command. Use: Put <data>, Get, or Clear");
  }
}
}

//void storeDataToFile(String data) {
void storeDataToFile(const uint8_t* data, int length) {
  File file = LittleFS.open("/ble_data.txt", "a");
  if (file) {

    file.write(data, length);
    file.close();
    Serial.println("Data saved to file");
  } else {
    Serial.println("Failed to open file for writing");
  }
}

void sendStoredData() {
  File file = LittleFS.open("/ble_data.txt", "r");
  if (file) {
 
    const int chunckSize = 20;
    char buffer[chunckSize+1];
    int bytesRead;
    bool hasSentData = false;

    while ((bytesRead = file.readBytes(buffer, chunckSize)) > 0){
      buffer[bytesRead] = '\0';
      txCharacteristic.writeValue((char*)buffer, chunckSize, false);
      hasSentData = true;
      delay(20);
      Serial.print("Sent Chunck: ");
      Serial.println(bytesRead);
    }

    file.close();

    if (hasSentData) {
      uint8_t end = CMD_END;
      txCharacteristic.writeValue(end, 1);
      Serial.println("All Data Sent");
    } else{
      txCharacteristic.writeValue("No data stored");
    }
  } else {
      txCharacteristic.writeValue("No data file found");
  }

}

void clearStoredData() {
  if (LittleFS.remove("/ble_data.txt")) {
    Serial.println("Data file deleted");
  } else {
    Serial.println("Failed to delete data file");
  }
}

String uint8_tToString(const uint8_t* data, int length){

  String dataString = "";
        for (int i = 0; i < length; i++){
          dataString += (char)data[i];
        }
  return dataString;
}