# send_test_no_xonxoff.py
# -*- coding: utf-8 -*-

import serial
import time

PORT = "/dev/ttyUSB0"
BAUD = 4800

data = b"%\r\nO0001\r\nM30\r\n%\r\n"

ser = serial.Serial(
    port=PORT,
    baudrate=BAUD,
    bytesize=serial.SEVENBITS,
    parity=serial.PARITY_EVEN,
    stopbits=serial.STOPBITS_TWO,
    timeout=1,
    write_timeout=2,
    xonxoff=False,
    rtscts=False,
    dsrdtr=False
)

try:
    ser.dtr = True
    ser.rts = True
except:
    pass

input("กด READ ที่ Fanuc ให้ LSK กระพริบก่อน แล้วกด Enter...")

for line in data.splitlines(True):
    ser.write(line)
    ser.flush()
    print(line)
    time.sleep(0.2)

ser.close()
print("done")