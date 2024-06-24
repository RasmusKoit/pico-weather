# Pico Weather Station

## Overview

The Pico Weather Station is a project designed to display both indoor and outdoor weather conditions using a Raspberry Pi Pico microcontroller. This project utilizes various sensors and an OLED display to provide real-time weather updates.

## Features

- Displays current date and time
- Monitors indoor temperature and humidity using a DHT22 sensor
- Fetches and displays outdoor temperature and humidity from an online API
- Shows battery status
- Connects to WiFi for online data retrieval
- Battery-powered operation (optional)

## Components

- Raspberry Pi Pico (W)
- DHT22 temperature and humidity sensor
- SSD1306 OLED display
- WiFi module (built-in on some Pico models or external)
- TP4056 battery charger module (optional)
- 18650 battery(s) (optional)

## Prerequisites

- MicroPython installed on Raspberry Pi Pico
- Required libraries: `machine`, `network`, `urequests`, `dht`, `ssd1306`
- A WiFi network to connect to

## Setup and Installation

1. **Hardware Connections**:
    - Connect the DHT22 sensor to the Raspberry Pi Pico.
    - Connect the SSD1306 OLED display to the Pico via I2C (SCL to GP19, SDA to GP18).
    - Connect the battery (if using one) and ensure it can be read via the VSYS pin (GP29).

2. **Upload Code to Pico**:
    - Copy the `main.py` file (this project's main code) to the Raspberry Pi Pico.
    - Copy the `NETINFO.example.py` file to `NETINFO.py` and update the variables with your WiFi credentials and GPS coordinates.
    - Ensure all required libraries are available on the Pico.

3. **Configuration**:
    - Copy NETINFO.example.py to NETINFO.py and update variables and gps coordinates.

    ```python
    WIFI_SSID = 'ssid'
    WIFI_PASSWORD = 'password'
    WEATHER_API_URL = "https://api.met.no/weatherapi/locationforecast/2.0/compact?lat=55.000&lon=55.000"
    TIME_API_URL = 'http://worldtimeapi.org/api/timezone/Europe/Tallinn'
    ```

## Code Explanation

### Main Functions

1. **init()**
    - Initializes the display, connects to WiFi, sets the RTC time, and starts the main program loop.

2. **init_display()**
    - Displays initial startup information on the OLED screen.

3. **wifi_action(activate: bool)**
    - Manages the WiFi connection. If `activate` is `True`, it connects to the WiFi; otherwise, it disconnects.

4. **query_outside() -> tuple**
    - Fetches external temperature and humidity from the weather API.

5. **get_time() -> tuple**
    - Retrieves the current time from an online time API and adjusts for the local timezone.

6. **set_pad(gpio, value)**
    - Sets the pad control register for a given GPIO pin.

7. **get_pad(gpio)**
    - Gets the current pad control register value for a given GPIO pin.

8. **read_vsys()**
    - Reads the system voltage to determine battery status.

9. **draw_battery()**
    - Draws the battery status on the OLED display.

10. **draw_custom_char()**
    - Draws a custom character on the OLED display.

11. **run_program()**
    - Main loop that continuously updates the display with current time, indoor and outdoor temperature, humidity, and battery status.

## Usage

1. Power on the Raspberry Pi Pico.
2. The device will automatically connect to the configured WiFi network.
3. It will fetch the current time and outdoor weather data, then start displaying the information.
4. The display updates every 5 seconds with the latest indoor sensor readings and every 60 minutes with new outdoor data.

## Troubleshooting

- Ensure all hardware connections are secure.
- Check WiFi credentials and availability.
- Verify that the required libraries are correctly installed on the Pico.

## License

This project is licensed under the MIT License. See the `LICENSE` file for more details.

