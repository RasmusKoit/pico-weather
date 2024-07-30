from time import sleep, sleep_ms, localtime
from machine import Pin, SoftI2C, RTC, ADC, mem32, lightsleep
from ssd1306 import SSD1306_I2C  # type: ignore
from NETINFO import WIFI_SSID, WIFI_PASSWORD, WEATHER_API_URL, TIME_API_URL
import network  # type: ignore
import urequests  # type: ignore
import dht  # type: ignore

# Pins
LED_PIN = Pin("LED", Pin.OUT)
SCL_PIN = Pin(17)
SDA_PIN = Pin(16)
DHT22_PIN = Pin(21)
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
    init_display(False, False, False)
    wifi_action(True)
    init_display(True, False, False)
    rtc.datetime(get_time())
    init_display(True, True, False)
    run_scenes()


def init_display(
    wifi_status: bool = False, time_status: bool = False, sensor_status: bool = False
):
    """Initialize and display startup information."""
    display.fill(0)
    display.text("Pico Weather", 0, 5)
    display.text("Initializing...", 0, 18)
    display.hline(0, 28, 128, 1)
    display.text("WiFi:    " + ("OK" if wifi_status else "..."), 0, 30)
    display.text("Time:    " + ("OK" if time_status else "..."), 0, 40)
    display.text("Sensors: " + ("OK" if sensor_status else "..."), 0, 50)
    display.show()


def wifi_action(activate: bool) -> None:
    """Manage the WiFi connection."""
    if activate:
        # Check if WiFi is already active and connected
        if wifi.active() and wifi.isconnected():
            print("WiFi already active and connected")
            return

        if not wifi.active():
            print("Activating WiFi")
            wifi.active(True)

        # Check if WiFi is connected, if not, attempt to connect
        if not wifi.isconnected():
            wifi.connect(WIFI_SSID, WIFI_PASSWORD)
            timeout = 30  # Reduced timeout to 30 seconds
            while not wifi.isconnected() and timeout > 0:
                sleep(1)
                timeout -= 1
                print("Connecting to WiFi...")
            if wifi.isconnected():
                print("Connected to WiFi")
            else:
                print("Failed to connect to WiFi within 30 seconds")
        else:
            print("WiFi is already connected")
    else:
        if wifi.active():
            wifi.active(False)
            wifi.deinit()
            print("WiFi deactivated")
        else:
            print("WiFi is already deactivated")


def query_outside() -> list:
    """Query external weather data."""

    try:
        headers = {
            "User-Agent": "Pico Weather/1.0 github.com/rasmuskoit",
            "Accept": "application/json",
        }
        # Make sure wifi is active
        wifi_action(True)
        response = urequests.get(WEATHER_API_URL, headers=headers)
        # turn off wifi
        data = response.json()
        wifi_action(False)
        return data["properties"]["timeseries"][0:3]
    except Exception as e:
        print(f"Failed to get outside values: {e}")
        return []


def get_time() -> tuple:
    """Get the current time from an online API."""
    try:
        response = urequests.get(TIME_API_URL)
        data = response.json()
        unixtime = data["unixtime"]
        timezone_offset = data["raw_offset"] + data["dst_offset"]
        local_unixtime = unixtime + timezone_offset
        year, month, day, hour, minute, second, weekday, yearday = localtime(
            local_unixtime
        )
        return year, month, day, weekday, hour, minute, second, 0
    except Exception as e:
        print(f"Failed to get time: {e}")
        return 1970, 1, 1, 0, 0, 0, 0, 0


# Pad functions are needed to ensure stable WiFi connection
def set_pad(gpio, value):
    """Set pad control register for a given GPIO pin."""
    mem32[0x4001C000 | (4 + (4 * gpio))] = value


# Pad functions are needed to ensure stable WiFi connection
def get_pad(gpio):
    """Get the current pad control register value for a given GPIO pin."""
    return mem32[0x4001C000 | (4 + (4 * gpio))]


def read_vsys():
    """Read system voltage to determine battery status."""
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
        display.text("W", text_align, 25)
        display.text("I", text_align, 33)
        display.text("R", text_align, 41)
        display.text("E", text_align, 49)
    else:
        pixels = 36
        battery_percentage = (battery_voltage - 2.7) / (3.3 - 2.7) * 100
        print(f"Battery percentage: {battery_percentage:.1f}%")
        pixels_to_light = int(battery_percentage / 100 * pixels)
        display.fill_rect(107, 22 + pixels - pixels_to_light, 14, pixels_to_light, 1)


def draw_custom_char():
    """Draw a custom character on the display."""
    custom_pixels = [
        (1, 42),
        (1, 41),
        (2, 41),
        (2, 40),
        (3, 41),
        (3, 40),
        (4, 42),
        (4, 41),
        (5, 42),
        (5, 41),
        (6, 41),
        (6, 40),
    ]
    for x, y in custom_pixels:
        display.pixel(x, y, 1)


def read_dht22():
    # Read the DHT22 sensor values, try 3 times
    attempt = 0
    while attempt < 3:
        try:
            sensor_dht22.measure()
            # If sensor values are read successfully, break the loop
            home_humidity = sensor_dht22.humidity()
            home_temperature = sensor_dht22.temperature()
            # if temp is 0, retry
            if home_temperature != 0 and home_humidity != 0:
                break
            sleep(2)
            attempt += 1
        except OSError:
            print("Failed to read DHT22 sensor values")
            return 0, 0
    return home_temperature, home_humidity
def run_scenes():
    """Run the scenes."""
    try:
        scene = 0
        number_of_scenes = 2
        scene_duration = 15
        current_time_by_minute = rtc.datetime()[4] * 60 + rtc.datetime()[5]
        data = query_outside()
        home_temperature, home_humidity = read_dht22()
        init_display(True, True, True)
        sleep(2)
        while True:
            # Read the DHT22 sensor values
            home_temperature, home_humidity = read_dht22()
            # Calculate the current time in minutes
            current_time_minutes = rtc.datetime()[4] * 60 + rtc.datetime()[5]

            if current_time_minutes - current_time_by_minute >= 30:
                try:
                    print("Querying new outside values")
                    data = query_outside()
                    current_time_by_minute = current_time_minutes
                except MemoryError:
                    print("Memory allocation failed. Please try again later")
                except Exception as e:
                    print(f"Failed to get outside values: {e}")
            display.fill(0)
            if scene == 0:
                outside_temperature = data[0]["data"]["instant"]["details"][
                    "air_temperature"
                ]
                outside_humidity = data[0]["data"]["instant"]["details"][
                    "relative_humidity"
                ]
                current_weather(
                    home_temperature,
                    home_humidity,
                    outside_temperature,
                    outside_humidity,
                )
            elif scene == 1:
                forecast_weather(data)
            else:
                scene = 0
            scene = (scene + 1) % number_of_scenes
            display.show()
            # Try to light sleep to save power
            lightsleep(scene_duration * 1000)
            # sleep(scene_duration)
    except KeyboardInterrupt:
        print("Program stopped by user")
        wifi_action(False)
    except Exception as e:
        display.fill(0)
        display.text("Error occurred", 0, 5)
        display.text(str(e), 0, 20)
        print(f"Error occurred: {e}")


def get_timezone_offset(date_str) -> int:
    pico_hour = rtc.datetime()[4]
    date_hour = int(date_str[11:13])
    return pico_hour - date_hour


def current_weather(h_temp, h_hum, o_temp, o_hum):
    """Display the current weather."""
    # Display current weather
    date_formatted = "{:02d}.{:02d}.{:02d} {:02d}:{:02d}".format(
        rtc.datetime()[2],
        rtc.datetime()[1],
        rtc.datetime()[0] % 100,
        rtc.datetime()[4],
        rtc.datetime()[5],
    )
    display.text(date_formatted, int((128 - len(date_formatted) * 8) / 2), 0)
    display.hline(0, 14, 128, 1)
    display.text(f"Kodus {h_temp:.1f} C", 0, 20)
    display.text(f"      {h_hum:.1f} %", 0, 32)
    draw_custom_char()
    display.text(f"Oues  {o_temp:.1f} C", 0, 44)
    display.text(f"      {o_hum:.1f} %", 0, 56)
    draw_battery()


def get_datetime_hour(date_str: str, offset: int) -> str:
    # handle the case when number is larger than 24
    # handle the case when number is smaller than 0
    hour = int(date_str[11:13]) + offset
    if hour > 24:
        hour -= 24
    elif hour < 0:
        hour += 24
    # return the hour, add leading zero if needed
    return f"{hour:02d}"


def forecast_weather(weather_data: list):
    """Display the forecast weather."""
    tz_offset = get_timezone_offset(weather_data[0]["time"])
    title = "Ilmaprognoos"
    display.text(title, int((128 - len(title) * 8) / 2), 0)
    display.hline(0, 14, 128, 1)
    display.vline(0, 16, 48, 1)
    display.vline(42, 16, 48, 1)
    display.vline(84, 16, 48, 1)
    display.vline(127, 16, 48, 1)
    display.hline(0, 28, 128, 1)
    # Display hours and weather data
    for i in range(len(weather_data)):
        display.text(
            f"{get_datetime_hour(weather_data[i]['time'], tz_offset) }", i * 42 + 16, 18
        )
        display.text(
            f"{weather_data[i]['data']['instant']['details']['air_temperature']:.0f}C",
            i * 42 + 12,
            30,
        )
        display.text(
            f"{weather_data[i]['data']['instant']['details']['relative_humidity']:.0f}%",
            i * 42 + 12,
            42,
        )
        display.text(
            f"{weather_data[i]['data']['next_1_hours']['details']['precipitation_amount']:02.0f}mm",
            i * 42 + 5,
            54,
        )


# Start the program
init()
