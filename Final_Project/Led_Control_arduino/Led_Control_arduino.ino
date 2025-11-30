#include <Adafruit_NeoPixel.h>

#define PIN        6
#define NUMPIXELS  16

// standard setting for WS2812
Adafruit_NeoPixel pixels(NUMPIXELS, PIN, NEO_GRB + NEO_KHZ800);

void setup() {
  Serial.begin(9600); // Start listening on USB at 9600 speed
  pixels.begin();
  pixels.show(); // Clear all pixels to off
}

void loop() {
  // Is the Pi trying to talk to us?
  if (Serial.available() > 0) {
    
    // Read the incoming string until a newline character
    String command = Serial.readStringUntil('\n');
    command.trim(); // Remove whitespace
    
    // Parse the command "R,G,B"
    // Find the positions of the commas
    int firstComma = command.indexOf(',');
    int secondComma = command.indexOf(',', firstComma + 1);
    
    // If we found both commas, we have valid data
    if (firstComma > 0 && secondComma > 0) {
      int r = command.substring(0, firstComma).toInt();
      int g = command.substring(firstComma + 1, secondComma).toInt();
      int b = command.substring(secondComma + 1).toInt();
      
      setRingColor(r, g, b);
    }
  }
}

void setRingColor(int r, int g, int b) {
  for(int i=0; i<NUMPIXELS; i++) {
    pixels.setPixelColor(i, pixels.Color(r, g, b));
  }
  pixels.show();
}