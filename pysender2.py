# -*- coding: utf-8 -*-

import serial
import time
import os

PORT = "COM5"        # แก้เป็น COM ของ USB-RS232 เช่น COM1, COM3, COM5
BAUD = 4800          # ให้ตรงกับ Fanuc
GCODE_FILE = "test.nc"


def read_gcode_file(filename):
    if not os.path.exists(filename):
        raise Exception("File not found: " + filename)

    f = open(filename, "rb")
    data = f.read()
    f.close()

    # แปลง line ending ให้เป็น \n ก่อน
    data = data.replace(b"\r\n", b"\n")
    data = data.replace(b"\r", b"\n")

    raw_lines = data.split(b"\n")

    clean_lines = []

    for line in raw_lines:
        line = line.strip()

        if line != b"":
            # บังคับให้เหลือเฉพาะ ASCII
            # กันปัญหาภาษาไทยหรืออักขระแปลก ๆ
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


def main():
    print("Fanuc O-T RS232 Sender")
    print("----------------------")
    print("Port:", PORT)
    print("Baud:", BAUD)
    print("File:", GCODE_FILE)
    print("")

    data = read_gcode_file(GCODE_FILE)

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

    print("Opened port:", PORT)
    print("")
    print("Set Fanuc machine:")
    print("1. PROGRAM PROTECT = OFF")
    print("2. MODE = EDIT")
    print("3. Press PROGRAM / PRGRM")
    print("4. Press INPUT or READ > EXEC")
    print("5. Wait until LSK is blinking")
    print("")

    input("Press Enter to send G-code...")

    ser.reset_input_buffer()
    ser.reset_output_buffer()

    lines = data.splitlines(True)

    for line in lines:
        ser.write(line)
        ser.flush()

        # แสดงบรรทัดที่กำลังส่ง
        print(line.decode("ascii", "ignore").strip())

        # ถ้าเครื่องรับไม่ทัน เพิ่มเป็น 0.05 หรือ 0.10
        time.sleep(0.03)

    time.sleep(0.5)
    ser.close()

    print("")
    print("Done.")
    print("Check Fanuc memory for the program.")


if __name__ == "__main__":
    main()