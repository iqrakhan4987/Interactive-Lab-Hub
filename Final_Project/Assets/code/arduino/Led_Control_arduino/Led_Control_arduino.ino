#include <Adafruit_NeoPixel.h>

#define PIN        6
#define NUMPIXELS  16

Adafruit_NeoPixel pixels(NUMPIXELS, PIN, NEO_GRB + NEO_KHZ800);

void setup() {
  Serial.begin(9600);
  pixels.begin();
  pixels.show(); // Initialize off
}

void loop() {
  if (Serial.available() > 0) {
    // We expect "Red, Green, Blue"
    int r = Serial.parseInt();
    int g = Serial.parseInt();
    int b = Serial.parseInt();
    
    // Read the newline
    if (Serial.read() == '\n') {
      pixels.setBrightness(255);
      for(int i=0; i<NUMPIXELS; i++) {
        pixels.setPixelColor(i, pixels.Color(r, g, b));
      }
      pixels.show();
    }
  }
}
