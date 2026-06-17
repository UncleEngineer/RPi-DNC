# -*- coding: utf-8 -*-

import serial
import time
import sys

PORT = "/dev/ttyUSB0"
BAUD = 4800
OUT_FILE = "fanuc_received.nc"

# ถ้าไม่มีข้อมูลเข้าแล้วกี่วินาที ให้หยุดเอง
IDLE_TIMEOUT = 5.0


def main():
    print("Fanuc O-T RS232 Receiver for Raspberry Pi")
    print("-----------------------------------------")
    print("Port :", PORT)
    print("Baud :", BAUD)
    print("Save :", OUT_FILE)
    print("")

    ser = serial.Serial(
        port=PORT,
        baudrate=BAUD,
        bytesize=serial.SEVENBITS,
        parity=serial.PARITY_EVEN,
        stopbits=serial.STOPBITS_TWO,
        timeout=0.2,
        write_timeout=2,
        xonxoff=False,
        rtscts=False,
        dsrdtr=False
    )

    # เปิดสถานะ DTR/RTS ไว้ บางเครื่องต้องการเห็นว่าอุปกรณ์พร้อม
    try:
        ser.dtr = True
        ser.rts = True
    except:
        pass

    # ล้าง buffer
    try:
        ser.reset_input_buffer()
        ser.reset_output_buffer()
    except:
        ser.flushInput()
        ser.flushOutput()

    # ส่ง XON ไปหนึ่งครั้ง เผื่อเครื่องรอสัญญาณอนุญาตให้ส่ง
    try:
        ser.write(b"\x11")
        ser.flush()
    except:
        pass

    print("ตอนนี้ Raspberry Pi รอรับข้อมูลแล้ว")
    print("")
    print("ที่หน้า Fanuc ให้ทำประมาณนี้:")
    print("1. MODE = EDIT")
    print("2. กด PROGRAM / PRGRM")
    print("3. เรียกโปรแกรมที่ต้องการส่ง เช่น O0001")
    print("4. กด PUNCH / OUTPUT")
    print("5. กด EXEC ถ้ามี")
    print("")
    print("ถ้าข้อมูลเข้ามา จะเห็นตัวอักษรและ HEX ขึ้นบนจอ")
    print("กด Ctrl+C เพื่อหยุดเองได้")
    print("")

    f = open(OUT_FILE, "wb")

    got_data = False
    last_data_time = time.time()

    try:
        while True:
            data = ser.read(1)

            if data:
                got_data = True
                last_data_time = time.time()

                f.write(data)
                f.flush()

                value = data[0]
                ch = data.decode("ascii", "replace")

                if ch == "\r":
                    show = "\\r"
                elif ch == "\n":
                    show = "\\n"
                elif ch == "\x00":
                    show = "\\0"
                elif value < 32:
                    show = "CTRL"
                else:
                    show = ch

                print("RX: 0x%02X  %s" % (value, show))

            else:
                if got_data:
                    idle = time.time() - last_data_time
                    if idle > IDLE_TIMEOUT:
                        print("")
                        print("ไม่มีข้อมูลเข้าเพิ่ม %s วินาที หยุดรับข้อมูล" % IDLE_TIMEOUT)
                        break

    except KeyboardInterrupt:
        print("")
        print("หยุดโดยผู้ใช้")

    f.close()
    ser.close()

    print("")
    print("บันทึกไฟล์แล้ว:", OUT_FILE)


if __name__ == "__main__":
    main()