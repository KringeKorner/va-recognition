#include "driver/i2s_pdm.h"
#include "esp_log.h"
#include "driver/gpio.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#define LED_DA_GPIO   14
#define LED_CK_GPIO   15
#define I2S_WS_GPIO   17
#define I2S_CK_GPIO   16
#define I2S_D0_GPIO   18  // Mic0
#define I2S_D1_GPIO   19  // Mic1
#define I2S_D2_GPIO   20 // Mic2
#define I2S_D3_GPIO   21 // Mic3
#define CHANNELS 8

static const char *TAG = "SiPEED";
int16_t buffer[256];
size_t bytes_read;

void sipeed_leds_off(void)
{
    gpio_set_direction(LED_DA_GPIO, GPIO_MODE_OUTPUT);
    gpio_set_direction(LED_CK_GPIO, GPIO_MODE_OUTPUT);

    for (int i = 0; i < 32; i++) {
        gpio_set_level(LED_DA_GPIO, 0);
        gpio_set_level(LED_CK_GPIO, 1);
        gpio_set_level(LED_CK_GPIO, 0);
    }
    for (int led = 0; led < 12; led++) {
        uint32_t frame = 0xE0000000;
        for (int i = 31; i >= 0; i--) {
            gpio_set_level(LED_DA_GPIO, (frame >> i) & 1);
            gpio_set_level(LED_CK_GPIO, 1);
            gpio_set_level(LED_CK_GPIO, 0);
        }
    }
    for (int i = 0; i < 32; i++) {
        gpio_set_level(LED_DA_GPIO, 1);
        gpio_set_level(LED_CK_GPIO, 1);
        gpio_set_level(LED_CK_GPIO, 0);
    }
}

void app_main(void)
{
    esp_err_t ret;

    sipeed_leds_off();
    ESP_LOGI(TAG, "Disabling LEDS");

    i2s_chan_handle_t i2s_rx_handle = NULL;
    i2s_chan_config_t chan_cfg = I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM_0, I2S_ROLE_MASTER);

    ret = i2s_new_channel(&chan_cfg, NULL, &i2s_rx_handle);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to create I2S RX channel: %s", esp_err_to_name(ret));
        return;
    }

    i2s_pdm_rx_slot_config_t slot_cfg = I2S_PDM_RX_SLOT_DEFAULT_CONFIG(
        I2S_DATA_BIT_WIDTH_16BIT,
        I2S_SLOT_MODE_MONO
    );

    i2s_pdm_rx_clk_config_t clk_cfg = I2S_PDM_RX_CLK_DEFAULT_CONFIG(16000);

    i2s_pdm_rx_gpio_config_t gpio_cfg = {
        .clk = I2S_CK_GPIO,
        .dins = { I2S_D0_GPIO, I2S_D1_GPIO, I2S_D2_GPIO, I2S_D3_GPIO },
        .invert_flags = { .clk_inv = 0 }
    };

    i2s_pdm_rx_config_t pdm_cfg = {
        .clk_cfg = clk_cfg,
        .slot_cfg = slot_cfg,
        .gpio_cfg = gpio_cfg
    };

    ret = i2s_channel_init_pdm_rx_mode(i2s_rx_handle, &pdm_cfg);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to init PDM RX mode: %s", esp_err_to_name(ret));
        i2s_del_channel(i2s_rx_handle);
        return;
    }
    ESP_LOGI(TAG, "I2S PDM RX initialized successfully");

    ret = i2s_channel_enable(i2s_rx_handle);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to enable RX channel: %s", esp_err_to_name(ret));
        return;
    }
    
    while (1) {
        uint32_t *raw = (uint32_t*)buffer;

        for(int i = 0; i < 16; i++)
        {
            ESP_LOGI(TAG, "RAW[%d] = 0x%08X", i, raw[i]);
        }
    }
}