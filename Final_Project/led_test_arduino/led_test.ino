#include <Adafruit_NeoPixel.h>

#define PIN        6     // The Arduino pin connected to "Data In"
#define NUMPIXELS  16    // You have a 16-LED ring

// Setup the NeoPixel library
Adafruit_NeoPixel pixels(NUMPIXELS, PIN, NEO_GRB + NEO_KHZ800);

void setup() {
  pixels.begin(); // Initialize the ring
  pixels.setBrightness(50); // Set brightness to ~20% (Safe for USB power)
  pixels.show();  // Turn everything off to start
}

void loop() {
  // 1. Red Fill
  colorWipe(pixels.Color(255,   0,   0), 50); // Red
  
  // 2. Green Fill
  colorWipe(pixels.Color(  0, 255,   0), 50); // Green
  
  // 3. Blue Fill
  colorWipe(pixels.Color(  0,   0, 255), 50); // Blue

  // 4. Rainbow Cycle
  rainbow(10); 
}

// --- Helper Functions ---

// Fill the dots one after the other with a color
void colorWipe(uint32_t color, int wait) {
  for(int i=0; i<pixels.numPixels(); i++) {
    pixels.setPixelColor(i, color);
    pixels.show();
    delay(wait);
  }
}

// Rainbow cycle along the whole ring
void rainbow(int wait) {
  for(long firstPixelHue = 0; firstPixelHue < 5*65536; firstPixelHue += 256) {
    for(int i=0; i<pixels.numPixels(); i++) { 
      int pixelHue = firstPixelHue + (i * 65536L / pixels.numPixels());
      pixels.setPixelColor(i, pixels.gamma32(pixels.ColorHSV(pixelHue)));
    }
    pixels.show();
    delay(wait);
  }
}