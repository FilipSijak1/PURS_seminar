#include <Arduino.h>

int sensor_pin = A0;       //Sensor Pin
int relay_pin = 7;         //Relay Pin
int water_level_pin = A1;
void setup()
{
  Serial.begin(9600);
  pinMode(sensor_pin, INPUT);
   pinMode(relay_pin, OUTPUT);
  pinMode(water_level_pin, INPUT);
}

void loop()
{
  int sensor_data = analogRead(sensor_pin);
  int mappedMoistureLevel = map(sensor_data, 50, 595, 0, 100);
  int waterLevel = analogRead(water_level_pin);
  int mappedWaterLevel = map(waterLevel, 140, 670, 0, 100);
  Serial.print("Očitana vrijednost razine vode: ");
  Serial.println(waterLevel);
  Serial.print("Razina vode: ");
  Serial.print(mappedWaterLevel);
  Serial.println("%");
  Serial.print("Sensor_data:");
  Serial.print(sensor_data);
  Serial.print("\t | ");
  Serial.print("Vlaznost tla: ");
  Serial.print(mappedMoistureLevel);
  Serial.println("%");
  
  if(sensor_data < 100 && waterLevel > 550)
  {
    Serial.println("No moisture, Soil is dry");
    digitalWrite(relay_pin, HIGH);
  }
  else if(sensor_data <= 300 && sensor_data <= 450 & waterLevel < 550)
  {
    Serial.println("There is some moisture, Soil is medium");
    digitalWrite(relay_pin, LOW);
  }
  else if(sensor_data > 450)
  {
    Serial.println("Soil is wet");
    digitalWrite(relay_pin, LOW);
  }

  delay(100);
    }