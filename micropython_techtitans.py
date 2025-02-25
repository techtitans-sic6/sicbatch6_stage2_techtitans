from machine import Pin, SoftI2C, ADC
import ssd1306
import dht
import time
import network
from umqtt.simple import MQTTClient
import _thread
import urequests  # Library untuk HTTP request

# Konfigurasi OLED
SCREEN_WIDTH = 128
SCREEN_HEIGHT = 64
OLED_ADDR = 0x3C

# Konfigurasi pin
DHTPIN = Pin(4)
DHTTYPE = dht.DHT11
PIR_PIN = Pin(27, Pin.IN)
LDR_PIN = ADC(Pin(34))  # Gunakan ADC Pin 34
LDR_PIN.atten(ADC.ATTN_11DB)  # Ubah ke mode 12-bit agar bisa membaca 0-3.3V
LDR_PIN.width(ADC.WIDTH_12BIT)  # Gunakan 12-bit resolusi (0-4095)

BUZZER_PIN = Pin(23, Pin.OUT)

LED_PIR = Pin(5, Pin.OUT)
LED_WIFI = Pin(18, Pin.OUT)
LED_LIGHT = Pin(19, Pin.OUT)

# Inisialisasi sensor dan OLED
i2c = SoftI2C(scl=Pin(22), sda=Pin(21))
display = ssd1306.SSD1306_I2C(SCREEN_WIDTH, SCREEN_HEIGHT, i2c, addr=OLED_ADDR)
dht_sensor = dht.DHT11(DHTPIN)

# Konfigurasi WiFi
SSID = "SSID HD"
PASSWORD = "123123123"
wlan = network.WLAN(network.STA_IF)

# Konfigurasi MQTT (Ubidots)
MQTT_SERVER = "industrial.api.ubidots.com"
MQTT_TOKEN = "BBUS-YT8iUvwlkGa4yTh672cO3PjcFR8mzw"
DEVICE_LABEL = "edunudge_ai_tech_titans"
TOPIC = "/v1.6/devices/edunudge_ai_tech_titans"

# Konfigurasi API Flask (MongoDB)
FLASK_API_URL = "http://192.168.104.236:5000/save"  # Ganti dengan IP server Flask Anda

# Variabel Global
wifi_connected = False
mqtt_client = None
last_pir_time = 0
pir_debounce_time = 3000  # 3 detik debounce

# Fungsi untuk menghubungkan WiFi
def connect_wifi():
    global wifi_connected
    wlan.active(True)
    wlan.disconnect()
    wlan.connect(SSID, PASSWORD)
    start_time = time.ticks_ms()
    
    while not wlan.isconnected():
        if time.ticks_diff(time.ticks_ms(), start_time) > 5000:  # Timeout 5 detik
            print("WiFi gagal terhubung! Melanjutkan tanpa WiFi.")
            wifi_connected = False
            return
        time.sleep(0.5)
    
    print("WiFi Terhubung!")
    wifi_connected = True

# Fungsi untuk menghubungkan MQTT
def connect_mqtt():
    global mqtt_client
    try:
        mqtt_client = MQTTClient("ESP32_Client", MQTT_SERVER, user=MQTT_TOKEN, password="")
        mqtt_client.connect()
        print("MQTT Terhubung!")
    except Exception as e:
        print("Gagal menghubungkan MQTT:", e)
        mqtt_client = None

# Fungsi untuk mengirim data ke MongoDB melalui API Flask
def send_to_mongodb(temp, hum, light, motion):
    try:
        payload = {
            "temp": temp,
            "hum": hum,
            "light": light,
            "motion": motion
        }
        headers = {"Content-Type": "application/json"}
        response = urequests.post(FLASK_API_URL, json=payload, headers=headers)
        print("Response dari MongoDB API:", response.text)
        response.close()
    except Exception as e:
        print("Gagal mengirim data ke MongoDB:", e)

# Fungsi untuk mengecek status WiFi setiap 1 detik
def check_wifi_status():
    global wifi_connected, mqtt_client
    while True:
        if wlan.isconnected():
            if not wifi_connected:
                print("WiFi Kembali Terhubung!")
                wifi_connected = True
                LED_WIFI.value(1)
                connect_mqtt()  # Reconnect MQTT jika WiFi kembali
        else:
            if wifi_connected:
                print("WiFi Terputus!")
                wifi_connected = False
                LED_WIFI.value(0)
        
        time.sleep(1)  # Cek WiFi setiap 1 detik

# Mulai thread untuk monitoring WiFi
_thread.start_new_thread(check_wifi_status, ())

# Inisialisasi Sistem
print("Memulai sistem...")
display.fill(0)
display.text("EduNudge AI", 0, 0)
display.text("Memulai Sistem...", 0, 10)
display.show()
time.sleep(2)

# Koneksi awal
connect_wifi()
if wifi_connected:
    connect_mqtt()

# Loop utama
while True:
    try:
        # Baca sensor DHT11
        dht_sensor.measure()
        temperature = dht_sensor.temperature()
        humidity = dht_sensor.humidity()
    except OSError as e:
        print("Gagal membaca sensor DHT11:", e)
        temperature = 0
        humidity = 0

    # Baca sensor lainnya
    movement = PIR_PIN.value()
    light_level = LDR_PIN.read()

    # Deteksi gerakan dengan debounce
    if movement == 1 and time.ticks_diff(time.ticks_ms(), last_pir_time) > pir_debounce_time:
        last_pir_time = time.ticks_ms()
        LED_PIR.value(1)
        BUZZER_PIN.value(1)
        time.sleep(0.5)
        BUZZER_PIN.value(0)
    else:
        LED_PIR.value(0)

    # Indikator pencahayaan
    if light_level < 500:
        LED_LIGHT.value(1)
        BUZZER_PIN.value(1)
        time.sleep(0.5)
        BUZZER_PIN.value(0)
    else:
        LED_LIGHT.value(0)

    # Update status WiFi & tampilkan di OLED
    display.fill(0)
    display.text("WiFi  : " + ("CONNECTED" if wifi_connected else "DISCONNECTED"), 0, 0)
    display.text("Temp  : {} C".format(temperature), 0, 10)
    display.text("Humi  : {} %".format(humidity), 0, 20)
    display.text("Light : {}".format(light_level), 0, 30)
    display.text("Motion: " + ("DETECTED" if movement == 1 else "NO"), 0, 40)
    display.show()

    # Kirim data ke Ubidots jika WiFi tersedia
    if wifi_connected and mqtt_client:
        payload = '{{"temp": {}, "hum": {}, "light": {}, "motion": {}}}'.format(
            temperature, humidity, light_level, movement)
        try:
            mqtt_client.publish(TOPIC, payload)
            print("Data dikirim ke Ubidots:", payload)
        except Exception as e:
            print("Gagal mengirim data ke Ubidots:", e)

    # Kirim data ke MongoDB jika WiFi tersedia
    if wifi_connected:
        send_to_mongodb(temperature, humidity, light_level, movement)

    time.sleep(1)  # Tunggu 1 detik sebelum loop berikutnya