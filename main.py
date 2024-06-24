from time import sleep, sleep_ms, localtime
from machine import Pin, SoftI2C, RTC, ADC, mem32
from ssd1306 import SSD1306_I2C
from NETINFO import WIFI_SSID, WIFI_PASSWORD, WEATHER_API_URL, TIME_API_URL
import network
import urequests
import dht


# Pins
LED_PIN = Pin("LED", Pin.OUT)
SCL_PIN = Pin(19)
SDA_PIN = Pin(18)
DHT22_PIN = Pin(27)
CS_PIN = Pin(25, Pin.OUT)
VSYS_PIN = Pin(29)

# Initial Setup
CS_PIN.value(1)
sleep_ms(100)
VSYS_ADC = ADC(VSYS_PIN)
sleep_ms(100)
i2c = SoftI2C(scl=SCL_PIN, sda=SDA_PIN)
sleep_ms(100)
display = SSD1306_I2C(128, 64, i2c)
sensor_dht22 = dht.DHT22(DHT22_PIN)
wifi = network.WLAN(network.STA_IF)
rtc = RTC()

def init():
    """Initialize the system components and start the program."""
    init_display()
    wifi_action(True)
    rtc.datetime(get_time())
    run_program()

def init_display():
    """Initialize and display startup information."""
    display.fill(0)
    display.text('Pico Weather', 0, 5)
    display.text('v1.0', 0, 18)
    display.text('by Rasmus Koit', 0, 30)
    display.text('Initializing...', 0, 50)
    display.show()

def wifi_action(activate: bool) -> None:
    """Manage the WiFi connection."""
    if activate:
        wifi.active(True)
        wifi.connect(WIFI_SSID, WIFI_PASSWORD)
        timeout = 60
        while not wifi.isconnected() and timeout > 0:
            sleep(1)
            timeout -= 1
            print('Connecting to WiFi...')
        if wifi.isconnected():
            print('Connected to WiFi')
        else:
            print('Failed to connect to WiFi within 60 seconds')
    else:
        wifi.active(False)
        print('WiFi deactivated')

def query_outside() -> tuple:
    """Query external weather data."""
    try:
        headers = {
            "User-Agent": "Pico Weather/1.0 github.com/rasmuskoit",
            "Accept": "application/json"
        }
        response = urequests.get(WEATHER_API_URL, headers=headers)
        data = response.json()
        air_temperature = data['properties']['timeseries'][0]['data']['instant']['details']['air_temperature']
        moisture = data['properties']['timeseries'][0]['data']['instant']['details']['relative_humidity']
        return air_temperature, moisture
    except Exception as e:
        print(f'Failed to get outside values: {e}')
        return 0, 0

def get_time() -> tuple:
    """Get the current time from an online API."""
    try:
        response = urequests.get(TIME_API_URL)
        data = response.json()
        unixtime = data['unixtime']
        timezone_offset = data['raw_offset'] + data['dst_offset']
        local_unixtime = unixtime + timezone_offset
        year, month, day, hour, minute, second, weekday, yearday = localtime(local_unixtime)
        return year, month, day, weekday, hour, minute, second, 0
    except Exception as e:
        print(f'Failed to get time: {e}')
        return 1970, 1, 1, 0, 0, 0, 0, 0

def set_pad(gpio, value):
    mem32[0x4001c000 | (4 + (4 * gpio))] = value

def get_pad(gpio):
    return mem32[0x4001c000 | (4 + (4 * gpio))]

def read_vsys():
    conversion_factor = 3.3 / 65535
    oldpad = get_pad(29)
    set_pad(29, 128)  # no pulls, no output, no input
    adc_vsys = ADC(3)
    vsys = adc_vsys.read_u16() * 3.0 * conversion_factor
    set_pad(29, oldpad)
    return vsys

def draw_battery():
    """Draw the battery status on the display."""
    battery_voltage = read_vsys()
    display.rect(105, 20, 18, 40, 1)
    display.rect(104, 19, 20, 42, 1)
    display.fill_rect(108, 16, 12, 4, 1)
    if battery_voltage > 4.5:
        text_align = 110
        display.text('W', text_align, 25)
        display.text('I', text_align, 33)
        display.text('R', text_align, 41)
        display.text('E', text_align, 49)
    else:
        pixels = 36
        battery_percentage = (battery_voltage - 2.7) / (3.3 - 2.7) * 100
        print(f'Battery percentage: {battery_percentage:.1f}%')
        pixels_to_light = int(battery_percentage / 100 * pixels)
        display.fill_rect(107, 22 + pixels - pixels_to_light, 14, pixels_to_light, 1)

def draw_custom_char():
    """Draw a custom character on the display."""
    custom_pixels = [(1, 42), (1, 41), (2, 41), (2, 40), (3, 41), (3, 40), (4, 42), (4, 41), (5, 42), (5, 41), (6, 41), (6, 40)]
    for x, y in custom_pixels:
        display.pixel(x, y, 1)

def run_program():
    """Main program loop."""
    try:
        current_time_by_minute = rtc.datetime()[4] * 60 + rtc.datetime()[5]
        sensor_dht22.measure()
        home_humidity = sensor_dht22.humidity()
        home_temperature = sensor_dht22.temperature()
        out_temperature, out_humidity = query_outside()
        while True:
            if rtc.datetime()[4] * 60 + rtc.datetime()[5] - current_time_by_minute >= 35:
                try:
                    print('Querying new outside values')
                    print(f'Current time: {rtc.datetime()}')
                    print(f'Current values: {home_temperature}, {home_humidity}')
                    out_temperature, out_humidity = query_outside()
                    print(f'New values: {out_temperature}, {out_humidity}')
                    current_time_by_minute = rtc.datetime()[4] * 60 + rtc.datetime()[5]
                except MemoryError:
                    print("Memory allocation failed. Please try again later.")
            else:
                print(f'Current time: {rtc.datetime()[4] * 60 + rtc.datetime()[5] - current_time_by_minute}')
            
            sensor_dht22.measure()
            home_humidity = sensor_dht22.humidity()
            home_temperature = sensor_dht22.temperature()
            date_formatted = "{:02d}.{:02d}.{:02d} {:02d}:{:02d}".format(rtc.datetime()[2], rtc.datetime()[1], rtc.datetime()[0] % 100, rtc.datetime()[4], rtc.datetime()[5])

            display.fill(0)
            display.text(date_formatted, int((128 - len(date_formatted) * 8) / 2), 0)
            display.text(f'Kodus {home_temperature:.1f} C', 0, 20)
            display.text(f'      {home_humidity:.1f} %', 0, 32)
            draw_custom_char()
            display.text(f'Oues  {out_temperature:.1f} C', 0, 44)
            display.text(f'      {out_humidity:.1f} %', 0, 56)
            draw_battery()
            display.show()
            sleep(5)
    except KeyboardInterrupt:
        print('Program stopped by user')
        wifi_action(False)
    except Exception as e:
        print(f'Error occurred: {e}')

# Start the program
init()