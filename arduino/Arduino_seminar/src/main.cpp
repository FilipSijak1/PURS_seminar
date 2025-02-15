#include <Arduino.h>
#include <WiFiS3.h>
#include <PubSubClient.h>

// WiFi credentials
const char* ssid = "ZTE_0DCCF9";
const char* password = "5QF7B7J6B6";

// MQTT broker details
const char* mqtt_server = "192.168.0.3";
const int mqtt_port = 1883;

// MQTT topics
const char* sensor_data_topic = "sensor/data";

WiFiClient espClient;
PubSubClient client(espClient);

int sensor_pin = A0;       // Senzor vlage tla
int water_level_pin = A1;  // Senzor razine vode
int red_led = 6;           // Crvena LED (Pumpa ugašena)
int green_led = 5;         // Zelena LED (Pumpa radi)
int relay_pin = 7;         // Relay Pin

// Function declarations
void setup_wifi();
void callback(char* topic, byte* payload, unsigned int length);
void reconnect();

void setup() {
  Serial.begin(9600);
  pinMode(sensor_pin, INPUT);
  pinMode(water_level_pin, INPUT);
  pinMode(red_led, OUTPUT);
  pinMode(green_led, OUTPUT);
  pinMode(relay_pin, OUTPUT);

  Serial.println("Starting setup...");
  setup_wifi();
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);
  Serial.println("Setup complete.");
}

void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);

  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("WiFi connected");
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());
}

void callback(char* topic, byte* payload, unsigned int length) {
  String message;
  for (unsigned int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  Serial.print("Message arrived [");
  Serial.print(topic);
  Serial.print("] ");
  Serial.println(message);

  if (String(topic) == "control/watering_status") {
    if (message == "true") {
      digitalWrite(relay_pin, HIGH);
    } else {
      digitalWrite(relay_pin, LOW);
    }
  }
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    if (client.connect("ArduinoClient")) {
      Serial.println("connected");
      client.subscribe("control/watering_status");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      delay(5000);
    }
  }
}

void loop() {
  if (WiFi.status() == WL_CONNECTED && !client.connected()) {
    reconnect();
  }
  if (WiFi.status() == WL_CONNECTED) {
    client.loop();
  }

  int sensor_data = analogRead(sensor_pin);
  int mappedMoistureLevel = map(sensor_data, 50, 595, 0, 100);
  int waterLevel = analogRead(water_level_pin);
  int mappedWaterLevel = map(waterLevel, 15, 300, 0, 100);

  if (WiFi.status() == WL_CONNECTED) {
    String sensor_data_message = String(mappedMoistureLevel) + "," + String(mappedWaterLevel);
    client.publish(sensor_data_topic, sensor_data_message.c_str());
    Serial.print("Published sensor data: ");
    Serial.println(sensor_data_message);
  }

  Serial.println("==============");
  Serial.print("Senzor vlage tla (RAW): ");
  Serial.println(sensor_data);  // SIROVO očitanje tla

  Serial.print("Vlažnost tla: ");
  Serial.print(mappedMoistureLevel);
  Serial.println("%");

  Serial.print("Senzor razine vode (RAW): ");
  Serial.println(waterLevel);  // SIROVO očitanje vode

  Serial.print("Razina vode: ");
  Serial.print(mappedWaterLevel);
  Serial.println("%");
  Serial.println("==============");

  // --- LED signalizacija umjesto pumpe --- //
  if (mappedMoistureLevel < 30 && mappedWaterLevel > 25) {
    Serial.println("Tlo je suho → Pumpa se pali (ZELENA LED)!");
    digitalWrite(green_led, HIGH);  // Pumpa simulirana ZELENOM LED
    digitalWrite(red_led, LOW);     
  } else {
    Serial.println("Tlo je vlažno ili nema dovoljno vode → Pumpa je ugašena (CRVENA LED).");
    digitalWrite(green_led, LOW);   // Pumpa ne radi
    digitalWrite(red_led, HIGH);    
  }

  delay(1000); // Publish every 1 second
}