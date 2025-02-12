#include <Arduino.h>
#include <WiFiS3.h>
#include <PubSubClient.h>

// WiFi credentials
const char* ssid = "your_SSID";
const char* password = "your_PASSWORD";

// MQTT broker details
const char* mqtt_server = "your_MQTT_broker_address";
const int mqtt_port = 1883;
const char* mqtt_user = "your_MQTT_username";
const char* mqtt_password = "your_MQTT_password";

// MQTT topics
const char* moisture_topic = "sensor/moisture";
const char* water_level_topic = "sensor/water_level";
const char* watering_status_topic = "control/watering_status";

WiFiClient espClient;
PubSubClient client(espClient);

int sensor_pin = A0;       // Sensor Pin
int relay_pin = 7;         // Relay Pin
int water_level_pin = A1;

void setup() {
  Serial.begin(9600);
  pinMode(sensor_pin, INPUT);
  pinMode(relay_pin, OUTPUT);
  pinMode(water_level_pin, INPUT);

  setup_wifi();
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);
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
    } else {
      digitalWrite(relay_pin, LOW);
    }
  }
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    if (client.connect("ArduinoClient", mqtt_user, mqtt_password)) {
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
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  int sensor_data = analogRead(sensor_pin);
  int mappedMoistureLevel = map(sensor_data, 50, 595, 0, 100);
  int waterLevel = analogRead(water_level_pin);
  int mappedWaterLevel = map(waterLevel, 140, 670, 0, 100);

  String moisture_message = String(mappedMoistureLevel);
  String water_level_message = String(mappedWaterLevel);

  client.publish(moisture_topic, moisture_message.c_str());
  client.publish(water_level_topic, water_level_message.c_str());

  Serial.print("Sensor_data: ");
  Serial.print(sensor_data);
  Serial.print("\t | Vlaznost tla: ");
  Serial.print(mappedMoistureLevel);
  Serial.println("%");
  Serial.print("Očitana vrijednost razine vode: ");
  Serial.println(waterLevel);
  Serial.print("Razina vode: ");
  Serial.print(mappedWaterLevel);
  Serial.println("%");

  delay(10000); // Publish every 10 seconds
}