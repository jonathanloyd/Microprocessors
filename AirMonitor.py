#Author: Jonathan Loyd
#Description: Reads in data from an SDS011 Air Monitor, stores that run_info
#to a database, displays readings to a 16X2 LCD, and detects button presses
#to change the display for the LCD
#CSE525 Final Project

import threading
import time, serial, sqlite3
import Adafruit_CharLCD as LCD
import RPi.GPIO as GPIO

# Setup the serial connection with the SDS011 Air Monitor
ser = serial.Serial('/dev/ttyUSB0')

# Global variables for pm2.5 and pm10
pmtwofive = 0
pmten = 0

# For creating the thread
class myThread (threading.Thread):
    def __init__(self, threadID, name):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
    def run(self):
        print("Starting " + self.name)
        read_sensor(self.name)

# Thread to read sensor data
def read_sensor(threadName):
    global pmtwofive
    global pmten

    # Create & connect to database
    db = sqlite3.connect(r"/var/www/html/data.db")

    # Create empty tables
    db.execute("""
    CREATE TABLE IF NOT EXISTS "Data" (
    "ID" INT,
    "PM2.5" FLOAT,
    "PM10" FLOAT)
    """)
    db.commit()

    id = 0
    # Forever loop to get data
    while True:
        data = []
        for index in range(0,10):
            datum = ser.read()
            data.append(datum)
        pmtwofive = int.from_bytes(b''.join(data[2:4]), byteorder='little') / 10
        pmten = int.from_bytes(b''.join(data[4:6]), byteorder='little') / 10

        # Add Data to database
        db.execute("INSERT INTO Data VALUES (?, ?, ?)", (id, pmtwofive, pmten))
        db.commit()
        id += 1

# Create data thread
data_thread = myThread(1, "Data Thread")

# Start data thread
data_thread.start()

# Setup asynchronous button presses
def button_callback(channel):
    global counter
    # print("Button was pushed!")
    lcd.clear()
    if counter == 1:
        counter = 0
    else:
        counter += 1
    if counter == 0:
        message = "PM2.5:\n" + str(pmtwofive)
    elif counter == 1:
        message = "PM10:\n" + str(pmten)
    lcd.message(message)

try:
    # Setup GPIO for button
    counter = 0
    GPIO.setwarnings(False) # Ignore warning for now
    GPIO.setup(15, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) # Set pin 15 to be the button input pin and set initial value to be pulled low (off)
    GPIO.add_event_detect(15,GPIO.RISING,callback=button_callback) # Setup event on pin 15 (button) rising edge

    # LCD pin setup
    lcd_rs = 25
    lcd_en = 24
    lcd_d4 = 23
    lcd_d5 = 17
    lcd_d6 = 18
    lcd_d7 = 22
    lcd_backlight = 2

    # Define LCD column and row size for 16x2 LCD (using ACM1602A)
    lcd_columns = 16
    lcd_rows = 2

    # Setup the LCD controls
    lcd = LCD.Adafruit_CharLCD(lcd_rs, lcd_en, lcd_d4, lcd_d5, lcd_d6, lcd_d7, lcd_columns, lcd_rows, lcd_backlight)

    # Print message to LCD & terminal and sleep to wait for sensor to stabilize before reading measurements
    print("Waiting for monitor")
    lcd.message('Starting...')
    time.sleep(10)
    lcd.clear()

    # Loop forever to print out PM2.5 or PM10 data to lcd
    print("Reading data to LCD")
    while True:
        if counter == 0:
            message = "PM2.5:\n" + str(pmtwofive)
        elif counter == 1:
            message = "PM10:\n" + str(pmten)

        lcd.message(message)
        time.sleep(2)
        lcd.clear()

# Clean up GPIO on ctrl+c exit
except:
    GPIO.cleanup()

# Clean up GPIO on normal exit (shouldn't happen)
GPIO.cleanup()
