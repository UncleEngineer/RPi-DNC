# -*- coding: utf-8 -*-

import serial
import time
import os
import sys

PORT = "/dev/ttyUSB0"     # USB to RS232 บน Raspberry Pi
BAUD = 4800               # ต้องตรงกับ Fanuc
GCODE_FILE = "test.nc"    # ไฟล์ G-code


def read_gcode_file(filename):
    if not os.path.exists(filename):
        raise Exception("File not found: " + filename)

    f = open(filename, "rb")
    data = f.read()
    f.close()

    # แปลง line ending
    data = data.replace(b"\r\n", b"\n")
    data = data.replace(b"\r", b"\n")

    raw_lines = data.split(b"\n")
    clean_lines = []

    for line in raw_lines:
        line = line.strip()

        if line != b"":
            # ลบอักขระที่ไม่ใช่ ASCII กัน Fanuc งง
            line = line.decode("ascii", "ignore").encode("ascii")
            clean_lines.append(line)

    if len(clean_lines) == 0:
        raise Exception("Empty G-code file")

    # ใส่ % หัวท้าย ถ้ายังไม่มี
    if not clean_lines[0].startswith(b"%"):
        clean_lines.insert(0, b"%")

    if not clean_lines[-1].startswith(b"%"):
        clean_lines.append(b"%")

    # Fanuc รุ่นเก่าชอบ CRLF
    output = b"\r\n".join(clean_lines) + b"\r\n"

    return output


def send_gcode(filename):
    data = read_gcode_file(filename)

    print("Fanuc O-T DNC Sender for Raspberry Pi")
    print("-------------------------------------")
    print("Port :", PORT)
    print("Baud :", BAUD)
    print("File :", filename)
    print("")

    ser = serial.Serial(
        port=PORT,
        baudrate=BAUD,
        bytesize=serial.SEVENBITS,
        parity=serial.PARITY_EVEN,
        stopbits=serial.STOPBITS_TWO,
        timeout=0.2,
        write_timeout=2,
        xonxoff=True,
        rtscts=False,
        dsrdtr=False
    )

    # บาง USB-RS232 ต้องเปิด DTR/RTS
    try:
        ser.dtr = True
        ser.rts = True
    except:
        pass

    print("Serial opened.")
    print("")
    print("ตั้งหน้าเครื่อง Fanuc:")
    print("1. PROGRAM PROTECT = OFF")
    print("2. MODE = EDIT")
    print("3. กด PROGRAM / PRGRM")
    print("4. กด READ หรือ INPUT")
    print("5. รอ LSK กระพริบ")
    print("")

    input("ถ้า Fanuc พร้อมรับแล้ว กด Enter เพื่อส่ง...")

    ser.reset_input_buffer()
    ser.reset_output_buffer()

    lines = data.splitlines(True)

    for line in lines:
        ser.write(line)
        ser.flush()

        print(line.decode("ascii", "ignore").strip())

        # ถ้าเครื่องเก่ารับไม่ทัน เพิ่มเป็น 0.05 หรือ 0.10
        time.sleep(0.05)

    time.sleep(0.5)
    ser.close()

    print("")
    print("ส่งเสร็จแล้ว")
    print("เช็กที่ Fanuc ว่าโปรแกรมเข้า Memory หรือยัง")


if __name__ == "__main__":
    if len(sys.argv) >= 2:
        GCODE_FILE = sys.argv[1]

    send_gcode(GCODE_FILE)