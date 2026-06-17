import time
import serial

# 1. เปลี่ยนพอร์ตให้เป็นรูปแบบของ Linux/Raspberry Pi
# ปกติถ้าใช้สาย USB-to-RS232 จะเป็น /dev/ttyUSB0
SERIAL_PORT = "/dev/ttyUSB0"
BAUD_RATE = 4800  # ต้องตรงกับ Parameter ของ Fanuc (หรือลองลดเหลือ 2400 หากเจอ P/S Alarm)
TIMEOUT = 1

# 2. พาธของไฟล์ G-code บน Raspberry Pi (แนะนำให้ใส่ Full Path เพื่อความชัวร์)
GCODE_FILE_PATH = "/home/uncleengineer/Desktop/O5556"

try:
    # เปิดการเชื่อมต่อพอร์ต (ตั้งค่าโครงสร้างการรับส่งข้อมูลของ Fanuc)
    ser = serial.Serial(
        port=SERIAL_PORT,
        baudrate=BAUD_RATE,
        bytesize=serial.SEVENBITS,     # Fanuc 0T ใช้ 7 bits
        parity=serial.PARITY_EVEN,     # Fanuc 0T ใช้ Even parity
        stopbits=serial.STOPBITS_TWO,   # Stop bits 2
        xonxoff=True,                  # เปิด Software Handshaking แก้ปัญหา P/S Alarm 085
        rtscts=False,
        timeout=TIMEOUT,
    )

    print(f"เชื่อมต่อพอร์ต {SERIAL_PORT} สำเร็จ กำลังเตรียมส่งไฟล์...")

    # อ่านไฟล์ G-code
    with open(GCODE_FILE_PATH, "r", encoding="utf-8") as file:
        lines = file.readlines()

    print("เริ่มส่งข้อมูล... (กรุณากดปุ่ม READ ให้หน้าจอ Fanuc ขึ้น LSK กระพริบ)")
    time.sleep(2)  # หน่วงเวลาให้ผู้ใช้งานเตรียมตัว

    for line in lines:
        clean_line = line.strip()
        if not clean_line:
            continue

        # แปลงข้อความเป็น bytes และปิดท้ายด้วย \r\n (CR LF) ตามมาตรฐาน Fanuc EOB
        send_data = (clean_line + "\r\n").encode("ascii")

        ser.write(send_data)
        # สำหรับ Raspberry Pi แนะนำให้หน่วงเวลาเพิ่มขึ้นเล็กน้อย เพื่อไม่ให้ส่งข้อมูลเร็วเกินไป
        # ป้องกันอาการ Buffer Overflow (P/S Alarm 085) บนบอร์ด Fanuc รุ่นเก่า
        time.sleep(0.1) 

    print("ส่งไฟล์ G-code ไปยัง Fanuc 0T เรียบร้อยแล้ว!")

except serial.SerialException as e:
    print(f"เกิดข้อผิดพลาดเกี่ยวกับพอร์ตซีเรียล: {e}")
    print("คำแนะนำ: ตรวจสอบว่าสายหลุด หรือลองใช้คำสั่ง 'sudo chmod 666' เพื่อเปิดสิทธิ์พอร์ต")
except FileNotFoundError:
    print(f"ไม่พบไฟล์ G-code ในระบบ: {GCODE_FILE_PATH}")
finally:
    if "ser" in locals() and ser.is_open:
        ser.close()
        print("ปิดพอร์ตเชื่อมต่อเรียบร้อย")
