#include <Arduino.h>
#include <WiFiS3.h>
#include <PubSubClient.h>

// WiFi credentials
const char* ssid = "wifi_ssid";
const char* password = "wifi_password";

// MQTT broker details
const char* mqtt_server = "mqtt_broker_ip";
const int mqtt_port = 1883;

// MQTT topics
const char* sensor_data_topic = "sensor/data";
const char* watering_status_topic = "control/watering_status";

WiFiClient espClient;
PubSubClient client(espClient);

int sensor_pin = A0;       // Soil moisture sensor
int water_level_pin = A1;  // Water level sensor
int red_led = 6;           // Red LED (Pump off)
int green_led = 5;         // Green LED (Pump on)
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

  if (String(topic) == watering_status_topic) {
    if (message == "true") {
      digitalWrite(relay_pin, HIGH);
      digitalWrite(green_led, HIGH);  // Pump simulated by GREEN LED
      digitalWrite(red_led, LOW);
      Serial.println("Pump is on (GREEN LED)!");
    } else {
      digitalWrite(relay_pin, LOW);
      digitalWrite(green_led, LOW);   // Pump off
      digitalWrite(red_led, HIGH);
      Serial.println("Pump is off (RED LED).");
    }
  }
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    if (client.connect("ArduinoClient")) {
      Serial.println("connected");
      client.subscribe(watering_status_topic);
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
  Serial.print("Soil moisture sensor (RAW): ");
  Serial.println(sensor_data);  // RAW soil reading

  Serial.print("Soil moisture: ");
  Serial.print(mappedMoistureLevel);
  Serial.println("%");

  Serial.print("Water level sensor (RAW): ");
  Serial.println(waterLevel);  // RAW water reading

  Serial.print("Water level: ");
  Serial.print(mappedWaterLevel);
  Serial.println("%");
  Serial.println("==============");

  delay(1000); // Publish every 1 second
}