#include <Adafruit_NeoPixel.h>

Adafruit_NeoPixel pixel(1, 48, NEO_GRB + NEO_KHZ800);

void setup() {
  pixel.begin();
}

void loop() {
  pixel.setPixelColor(0, pixel.Color(255, 0, 0));
  pixel.show();
  delay(500);
  pixel.setPixelColor(0, pixel.Color(0, 255, 0));
  pixel.show();
  delay(500);
  pixel.setPixelColor(0, pixel.Color(0, 0, 255));
  pixel.show();
  delay(500);
}
