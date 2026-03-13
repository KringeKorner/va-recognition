#include <FastLED.h>
#include "driver/i2s.h"

// --- I2S Pins ---
#define I2S_BCK 4
#define I2S_WS 5
#define MIC_D0 6
#define MIC_D1 7
#define MIC_D2 15
#define MIC_D3 16

// --- LED Pins ---
#define LED_DA 17
#define LED_CK 18
#define NUM_LEDS 12

CRGB leds[NUM_LEDS];

// --- Audio Settings ---
#define SAMPLE_RATE 16000
#define BITS_PER_SAMPLE I2S_BITS_PER_SAMPLE_32BIT
#define DMA_BUF_LEN 128
#define DMA_BUF_COUNT 4
#define NUM_MICS 7

// I2S peripheral
#define I2S_PORT I2S_NUM_0

void setupI2S() {
  i2s_config_t i2s_config = {
      .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
      .sample_rate = SAMPLE_RATE,
      .bits_per_sample = BITS_PER_SAMPLE,
      .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
      .communication_format = I2S_COMM_FORMAT_I2S_MSB,
      .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
      .dma_buf_count = DMA_BUF_COUNT,
      .dma_buf_len = DMA_BUF_LEN,
      .use_apll = false,
      .tx_desc_auto_clear = false,
      .fixed_mclk = 0
  };

  i2s_pin_config_t pin_config = {
      .bck_io_num = I2S_BCK,
      .ws_io_num = I2S_WS,
      .data_out_num = I2S_PIN_NO_CHANGE,
      .data_in_num = MIC_D0  // we'll read D0-D3 sequentially via TDM slots
  };

  i2s_driver_install(I2S_PORT, &i2s_config, 0, NULL);
  i2s_set_pin(I2S_PORT, &pin_config);

  // TDM mode: 8 slots, 32-bit each (use only 7)
  i2s_set_sample_rates(I2S_PORT, SAMPLE_RATE);
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  // Setup LEDs
  FastLED.addLeds<WS2801, LED_DA, LED_CK, RGB>(leds, NUM_LEDS);
  FastLED.clear();
  FastLED.show();

  // Setup I2S
  setupI2S();
  Serial.println("Sipeed 6+1 mic array demo starting...");
}

void loop() {
  int32_t buffer[DMA_BUF_LEN];  // buffer for raw I2S data
  size_t bytes_read = 0;

  // Read I2S samples
  i2s_read(I2S_PORT, buffer, sizeof(buffer), &bytes_read, portMAX_DELAY);

  // For simplicity, take first sample from each mic (TDM slots)
  int16_t mics[NUM_MICS];
  // Mapping based on D0-D3 TDM order (adjust if your board differs)
  mics[0] = buffer[0] >> 16;  // MIC0
  mics[1] = buffer[1] >> 16;  // MIC1
  mics[2] = buffer[2] >> 16;  // MIC2
  mics[3] = buffer[3] >> 16;  // MIC3
  mics[4] = buffer[4] >> 16;  // MIC4
  mics[5] = buffer[5] >> 16;  // MIC5
  mics[6] = buffer[6] >> 16;  // MIC6

  // --- Update LEDs based on mic amplitudes ---
  for (int i = 0; i < NUM_LEDS; i++) {
    int mic_idx = i % NUM_MICS;
    int brightness = constrain(abs(mics[mic_idx]) / 256, 0, 255);
    leds[i] = CHSV((mic_idx * 36) % 256, 255, brightness);  // hue varies per mic
  }
  FastLED.show();

  // --- Print simplified audio levels ---
  Serial.print("Mic levels: ");
  for (int i = 0; i < NUM_MICS; i++) {
    Serial.print(abs(mics[i]));
    Serial.print(" ");
  }
  Serial.println();

  delay(50);  // adjust for readability and LED update speed
}
